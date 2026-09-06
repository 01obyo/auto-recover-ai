from supabase import Client, create_client

from config import SUPABASE_KEY, SUPABASE_URL

supabase: Client | None = (
    create_client(SUPABASE_URL, SUPABASE_KEY)
    if SUPABASE_URL and SUPABASE_KEY
    else None
)


def log_interaction(phone_number: str, role: str, content: str) -> None:
    """Persist a Twilio interaction in the shared messages table."""
    if supabase is None:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY are not configured"
        )

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