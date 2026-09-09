from fastapi import APIRouter, Form, Response, HTTPException
import os
import json
import re
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
        
        # 2. Fetch business profile with onboarding metadata
        business_query = supabase.table("businesses").select("*").eq("twilio_number", To).execute()
        
        if not business_query.data:
            business_id = None
            owner_phone = None
            system_prompt = "You are an AI assistant helping a customer with an inquiry. Be polite and brief."
        else:
            business = business_query.data[0]
            business_id = business["id"]
            owner_phone = business.get("owner_phone")
            
            # Dynamic system prompt built from business onboarding inputs
            biz_name = business.get("business_name", "our business")
            services = business.get("services_offered", "Contact us for service details.")
            hours = business.get("business_hours", "Standard operating hours.")
            address = business.get("location_address", "Available upon request.")
            faqs = business.get("faq_notes", "None.")
            custom_prompt = business.get("ai_system_prompt", "")

            system_prompt = f"""
You are an AI sales and support assistant for {biz_name}.

Business Profile Details:
- Services & Pricing: {services}
- Business Hours: {hours}
- Address/Location: {address}
- FAQs & Specific Notes: {faqs}

Additional Directives: {custom_prompt}

Instructions:
- Be concise, empathetic, and professional (under 3 sentences max).
- Assist the customer directly based on the business details above.
- If the customer wants to book or visit, politely prompt them for their preferred date and time.
- APPOINTMENT EXTRACTION: If the customer provides a specific date/time or intent to book, append a JSON block at the very end of your response strictly in this format:
  `||JSON:{{"booking_requested": true, "appointment_time": "YYYY-MM-DD HH:MM:SS", "customer_name": "Name if provided or Unknown"}}||`
  If no booking is requested, do NOT append the JSON block.
"""

        # 3. Fetch past conversation history (last 10 messages) for memory context
        history_context = ""
        if business_id:
            past_messages = (
                supabase.table("messages")
                .select("sender_role, message_body")
                .eq("business_id", business_id)
                .eq("customer_phone", From)
                .order("created_at", desc=True)
                .limit(10)
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

        # 5. Generate response with Dynamic Onboarding Prompt + Conversation Memory
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        full_prompt = f"""System Instructions:
{system_prompt}

Previous Conversation History:
{history_context if history_context else 'No previous history.'}

New Customer Message: {Body}"""

        response = model.generate_content(full_prompt)
        raw_reply = response.text.strip()

        # 6. Parse booking extraction and clean public message
        ai_reply = raw_reply
        booking_data = None

        if "||JSON:" in raw_reply:
            parts = raw_reply.split("||JSON:")
            ai_reply = parts[0].strip()
            json_str = parts[1].split("||")[0].strip()
            try:
                booking_data = json.loads(json_str)
            except Exception:
                booking_data = None

        # Execute Appointment Logging & Owner Escalation Alert
        if booking_data and booking_data.get("booking_requested") and business_id:
            # Insert into appointments table
            supabase.table("appointments").insert({
                "business_id": business_id,
                "customer_phone": From,
                "customer_name": booking_data.get("customer_name", "Unknown"),
                "appointment_time": booking_data.get("appointment_time"),
                "status": "scheduled"
            }).execute()

            # Escalate alert to business owner if owner_phone exists
            if owner_phone:
                alert_msg = f"🚨 NEW BOOKING ALERT: Customer {From} requested an appointment for {booking_data.get('appointment_time')}."
                await send_channel_response(
                    channel="sms",
                    recipient=owner_phone,
                    message=alert_msg,
                    business_twilio_number=To
                )

        # 7. Save clean AI response to Supabase with unified 'assistant' role
        if business_id:
            supabase.table("messages").insert({
                "business_id": business_id,
                "customer_phone": From,
                "sender_role": "assistant",
                "message_body": ai_reply
            }).execute()

        # 8. Dispatch reply back through matching channel
        await send_channel_response(
            channel=channel,
            recipient=From,
            message=ai_reply,
            business_twilio_number=To
        )

        return {"status": "success", "channel": channel, "reply": ai_reply, "booking_detected": bool(booking_data)}

    except Exception as e:
        fallback_msg = "Thanks for reaching out! We received your message and will get back to you shortly."
        return {"status": "error", "message": str(e), "fallback": fallback_msg}
