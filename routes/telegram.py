import os

import httpx
from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"].get("text", "")

        # Process message with Groq AI
        ai_response = f"Thanks for reaching out! I received your message: '{user_text}'. How can we assist you today?"

        # Send reply back to Telegram
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if bot_token:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": ai_response},
                )

    return {"status": "ok"}
