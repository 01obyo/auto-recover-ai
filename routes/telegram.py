import traceback

import httpx
from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool
from supabase import Client, create_client

from config import SUPABASE_KEY, SUPABASE_URL, TELEGRAM_BOT_TOKEN
from services.gemini_ai import get_ai_reply

router = APIRouter()
supabase: Client | None = (
    create_client(SUPABASE_URL, SUPABASE_KEY)
    if SUPABASE_URL and SUPABASE_KEY
    else None
)


def save_message(chat_id: int, role: str, content: str) -> None:
    if supabase is None:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are not configured")

    (
        supabase.table("messages")
        .insert({"chat_id": str(chat_id), "role": role, "content": content})
        .execute()
    )


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()

        message = data.get("message")
        if not message or not message.get("text"):
            return {"status": "ok"}

        chat_id = message["chat"]["id"]
        user_text = message["text"]
        await run_in_threadpool(save_message, chat_id, "user", user_text)

        ai_response = await run_in_threadpool(
            get_ai_reply, str(chat_id), user_text
        )

        if not TELEGRAM_BOT_TOKEN:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": ai_response},
            )
            response.raise_for_status()

        await run_in_threadpool(
            save_message, chat_id, "assistant", ai_response
        )

        return {"status": "ok"}
    except Exception as e:
        traceback.print_exc()
        print(f"TELEGRAM ERROR: {e}")
        return {"status": "error"}
