from fastapi import APIRouter, Form, Response
from twilio.twiml.messaging_response import MessagingResponse

from services.groq_ai import get_ai_reply

router = APIRouter()


@router.post("/sms")
async def handle_incoming_sms(From: str = Form(...), Body: str = Form(...)):
    """TwiML XML endpoint for live Twilio SMS webhook"""
    reply = get_ai_reply(user_id=From, message=Body)
    twiml = MessagingResponse()
    twiml.message(reply)
    return Response(content=str(twiml), media_type="application/xml")
