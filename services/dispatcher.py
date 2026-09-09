import os
import httpx
from twilio.rest import Client as TwilioClient

# Initialize Twilio client safely
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def send_channel_response(channel: str, recipient: str, message: str, business_twilio_number: str = None):
    """
    Sends the recovery message back through the appropriate channel:
    - 'sms': Standard SMS via Twilio
    - 'whatsapp': WhatsApp message via Twilio Sandbox/API
    - 'telegram': Telegram message via Bot API
    """
    channel = channel.lower().strip()
    
    if channel == "sms":
        if not twilio_client:
            raise ValueError("Twilio client is not configured.")
        from_num = business_twilio_number or os.getenv("TWILIO_PHONE_NUMBER")
        response = twilio_client.messages.create(
            body=message,
            from_=from_num,
            to=recipient
        )
        return {"status": "success", "provider_id": response.sid}

    elif channel == "whatsapp":
        if not twilio_client:
            raise ValueError("Twilio client is not configured.")
        from_num = business_twilio_number or os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
        to_whatsapp = recipient if recipient.startswith("whatsapp:") else f"whatsapp:{recipient}"
        from_whatsapp = from_num if from_num.startswith("whatsapp:") else f"whatsapp:{from_num}"
        
        response = twilio_client.messages.create(
            body=message,
            from_=from_whatsapp,
            to=to_whatsapp
        )
        return {"status": "success", "provider_id": response.sid}

    elif channel == "telegram":
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("Telegram Bot Token is not configured.")
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient() as client:
            payload = {
                "chat_id": recipient,
                "text": message
            }
            res = await client.post(url, json=payload)
            res.raise_for_status()
            return {"status": "success", "provider_data": res.json()}

    else:
        raise ValueError(f"Unsupported communication channel: {channel}")
