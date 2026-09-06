import logging

from supabase import Client, create_client

from config import SUPABASE_KEY, SUPABASE_URL

logger = logging.getLogger(__name__)

supabase: Client | None = (
    create_client(SUPABASE_URL, SUPABASE_KEY)
    if SUPABASE_URL and SUPABASE_KEY
    else None
)


def log_interaction(phone_number: str, role: str, content: str) -> bool:
    """Persist a Twilio interaction in the shared messages table."""
    if supabase is None:
        logger.warning(
            "Supabase unavailable; interaction was not persisted (role=%s)",
            role,
        )
        return False

    try:
        (
            supabase.table("messages")
            .insert(
                {
                    "chat_id": phone_number,
                    "role": role,
                    "content": content,
                }
            )
            .execute()
        )
        return True
    except Exception:
        logger.exception(
            "Supabase interaction logging failed; continuing without persistence "
            "(role=%s)",
            role,
        )
        return False