from fastapi import APIRouter, Request, Response
from twilio.twiml.messaging_response import MessagingResponse

from services.gemini_ai import get_ai_reply

router = APIRouter()


def _message_for_webhook(phone_number: str, body: str, call_status: str) -> str:
    if body.strip():
        return body.strip()
    if call_status.lower() in {"no-answer", "busy", "failed", "canceled", "completed"}:
        return (
            f"Missed call from {phone_number}. Follow up with this customer "
            "about booking a mobile auto-detailing service."
        )
    return f"Incoming call from {phone_number}. Follow up with this customer."


@router.post("/twilio/webhook")
@router.post("/sms")
async def handle_twilio_webhook(request: Request):
    """Handle incoming SMS messages and missed-call notifications from Twilio."""
    form = await request.form()
    phone_number = str(form.get("From") or form.get("from") or "").strip()
    body = str(form.get("Body") or form.get("body") or "")
    call_status = str(form.get("CallStatus") or form.get("call_status") or "")

    if not phone_number:
        return Response(
            content="Missing From phone number",
            status_code=400,
            media_type="text/plain",
        )

    message = _message_for_webhook(phone_number, body, call_status)
    reply = get_ai_reply(user_id=phone_number, message=message)
    twiml = MessagingResponse()
    twiml.message(reply)
    return Response(content=str(twiml), media_type="application/xml")
