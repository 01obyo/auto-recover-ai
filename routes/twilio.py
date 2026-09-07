from fastapi import APIRouter, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
import os
from supabase import create_client, Client
import google.generativeai as genai

router = APIRouter()

# Initialize Supabase & Gemini
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Use Service Role Key for backend writes
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@router.post("/twilio/webhook")
async def twilio_webhook(
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...)
):
    twiml = MessagingResponse()
    
    try:
        # 1. Fetch the business profile matching the recipient (To) phone number
        business_query = supabase.table("businesses").select("*").eq("twilio_number", To).execute()
        
        if not business_query.data:
            # Fallback if no business matches the incoming number
            business_name = "Our Business"
            system_prompt = "You are an AI assistant helping a customer with an inquiry. Be polite and brief."
            business_id = None
        else:
            business = business_query.data[0]
            business_id = business["id"]
            business_name = business["business_name"]
            system_prompt = business["ai_system_prompt"]

        # 2. Log customer message to Supabase
        if business_id:
            supabase.table("messages").insert({
                "business_id": business_id,
                "customer_phone": From,
                "sender_role": "customer",
                "message_body": Body
            }).execute()

        # 3. Generate response using Gemini with dynamic context
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"System Instructions: {system_prompt}\nCustomer Message: {Body}"
        
        response = model.generate_content(prompt)
        ai_reply = response.text.strip()

        # 4. Log AI response to Supabase
        if business_id:
            supabase.table("messages").insert({
                "business_id": business_id,
                "customer_phone": From,
                "sender_role": "ai",
                "message_body": ai_reply
            }).execute()

        twiml.message(ai_reply)

    except Exception as e:
        # Fallback response in case of API or DB failure
        twiml.message("Thanks for reaching out! We received your message and will get back to you shortly.")

    return Response(content=str(twiml), media_type="application/xml")
