from fastapi import APIRouter, Request, Response
from starlette.concurrency import run_in_threadpool
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

from config import TWILIO_AUTH_TOKEN
from services.gemini_ai import get_ai_reply
from services.supabase import log_interaction

router = APIRouter()
request_validator = RequestValidator(TWILIO_AUTH_TOKEN) if TWILIO_AUTH_TOKEN else None


async def _validate_twilio_request(request: Request, form: dict) -> bool:
    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        # Allow requests without signature (for testing UI)
        return True
    if request_validator is None:
        return False
    try:
        return request_validator.validate(str(request.url), form, signature)
    except Exception:
        return False

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
    form_values = {key: str(value) for key, value in form.items()}

    if not await _validate_twilio_request(request, form_values):
        return Response(
            content="Invalid Twilio signature",
            status_code=403,
            media_type="text/plain",
        )

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
    role = "inbound_message" if body.strip() else "inbound_call"
    await run_in_threadpool(log_interaction, phone_number, role, message)

    reply = get_ai_reply(user_id=phone_number, message=message)
    await run_in_threadpool(log_interaction, phone_number, "ai_reply", reply)

    twiml = MessagingResponse()
    twiml.message(reply)
    return Response(content=str(twiml), media_type="application/xml")
