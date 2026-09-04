import traceback

import httpx
from fastapi import APIRouter, Request

from config import TELEGRAM_BOT_TOKEN

router = APIRouter()


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()

        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            user_text = data["message"].get("text", "")

            # Process message with Groq AI
            ai_response = f"Thanks for reaching out! I received your message: '{user_text}'. How can we assist you today?"

            # Send reply back to Telegram
            if TELEGRAM_BOT_TOKEN:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                        json={"chat_id": chat_id, "text": ai_response},
                    )

        return {"status": "ok"}
    except Exception as e:
        traceback.print_exc()
        print(f"TELEGRAM ERROR: {e}")
        return {"status": "error"}
