from fastapi import APIRouter, Form, Response, HTTPException
import os
from config import supabase
import google.generativeai as genai
from services.dispatcher import send_channel_response

router = APIRouter()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@router.post("/twilio/webhook")
async def twilio_webhook(
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...)
):
    try:
        # 1. Determine channel type based on sender prefix
        channel = "whatsapp" if From.startswith("whatsapp:") else "sms"
        
        # 2. Fetch business profile
        business_query = supabase.table("businesses").select("*").eq("twilio_number", To).execute()
        
        if not business_query.data:
            business_id = None
            system_prompt = "You are an AI assistant helping a customer with an inquiry. Be polite and brief."
        else:
            business = business_query.data[0]
            business_id = business["id"]
            system_prompt = business["ai_system_prompt"]

        # 3. Fetch past conversation history (last 6 messages) for memory context
        history_context = ""
        if business_id:
            past_messages = (
                supabase.table("messages")
                .select("sender_role, message_body")
                .eq("business_id", business_id)
                .eq("customer_phone", From)
                .order("created_at", desc=True)
                .limit(6)
                .execute()
            )
            
            if past_messages.data:
                formatted_history = [
                    f"{msg['sender_role'].upper()}: {msg['message_body']}"
                    for msg in reversed(past_messages.data)
                ]
                history_context = "\n".join(formatted_history)

        # 4. Save incoming customer message
        if business_id:
            supabase.table("messages").insert({
                "business_id": business_id,
                "customer_phone": From,
                "sender_role": "customer",
                "message_body": Body
            }).execute()

        # 5. Generate response with System Prompt + Conversation History
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        full_prompt = f"""System Instructions: {system_prompt}

Previous Conversation History:
{history_context if history_context else 'No previous history.'}

New Customer Message: {Body}"""

        response = model.generate_content(full_prompt)
        ai_reply = response.text.strip()

        # 6. Save AI response to Supabase
        if business_id:
            supabase.table("messages").insert({
                "business_id": business_id,
                "customer_phone": From,
                "sender_role": "ai",
                "message_body": ai_reply
            }).execute()

        # 7. Dispatch back through the exact matching channel
        await send_channel_response(
            channel=channel,
            recipient=From,
            message=ai_reply,
            business_twilio_number=To
        )

        return {"status": "success", "channel": channel, "reply": ai_reply}

    except Exception as e:
        # Fallback safe response
        fallback_msg = "Thanks for reaching out! We received your message and will get back to you shortly."
        return {"status": "error", "message": str(e), "fallback": fallback_msg}
