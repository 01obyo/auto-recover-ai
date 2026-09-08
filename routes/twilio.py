from fastapi import APIRouter, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
import os
from config import supabase
import google.generativeai as genai

router = APIRouter()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@router.post("/twilio/webhook")
async def twilio_webhook(
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...)
):
    twiml = MessagingResponse()
    
    try:
        # 1. Fetch business profile
        business_query = supabase.table("businesses").select("*").eq("twilio_number", To).execute()
        
        if not business_query.data:
            business_id = None
            system_prompt = "You are an AI assistant helping a customer with an inquiry. Be polite and brief."
        else:
            business = business_query.data[0]
            business_id = business["id"]
            system_prompt = business["ai_system_prompt"]

        # 2. Fetch past conversation history (last 6 messages) for memory context
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
            
            # Format history in chronological order
            if past_messages.data:
                formatted_history = [
                    f"{msg['sender_role'].upper()}: {msg['message_body']}"
                    for msg in reversed(past_messages.data)
                ]
                history_context = "\n".join(formatted_history)

        # 3. Save incoming customer message
        if business_id:
            supabase.table("messages").insert({
                "business_id": business_id,
                "customer_phone": From,
                "sender_role": "customer",
                "message_body": Body
            }).execute()

        # 4. Generate response with System Prompt + Conversation History
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        full_prompt = f"""System Instructions: {system_prompt}

Previous Conversation History:
{history_context if history_context else 'No previous history.'}

New Customer Message: {Body}"""

        response = model.generate_content(full_prompt)
        ai_reply = response.text.strip()

        # 5. Save AI response
        if business_id:
            supabase.table("messages").insert({
                "business_id": business_id,
                "customer_phone": From,
                "sender_role": "ai",
                "message_body": ai_reply
            }).execute()

        twiml.message(ai_reply)

    except Exception as e:
        twiml.message("Thanks for reaching out! We received your message and will get back to you shortly.")

    return Response(content=str(twiml), media_type="application/xml")
