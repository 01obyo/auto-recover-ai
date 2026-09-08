import os
from supabase import create_client, Client

def _get_env(key: str) -> str:
    return os.environ.get(key, "").strip()

GEMINI_API_KEY = _get_env("GEMINI_API_KEY")
SUPABASE_URL = _get_env("SUPABASE_URL")
SUPABASE_KEY = _get_env("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = _get_env("TELEGRAM_BOT_TOKEN")
TWILIO_AUTH_TOKEN = _get_env("TWILIO_AUTH_TOKEN")
SENTRY_DSN = _get_env("SENTRY_DSN")

# Initialize shared Supabase client safely with fallback
try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    else:
        supabase = None
        print("Warning: Supabase credentials missing during config init.")
except Exception as e:
    supabase = None
    print(f"Warning: Failed to initialize Supabase client: {e}")

HUMAN_SYSTEM_PROMPT = """
You are Alex, the booking receptionist at Apex Mobile Auto Detailing.

BUSINESS KNOWLEDGE BASE:
- Full Interior & Exterior Sedan Detail: $180
- Full Interior & Exterior SUV / Truck Detail: $220
- Paint Correction & Polish: $350
- Ceramic Coating Package: $600
- Location: Mobile service (we come to the client's home or office).

HUMAN TEXTING RULES (CRITICAL):
1. Sound like a real business owner texting from a smartphone. Keep replies under 3 sentences.
2. NEVER sound like a generic bot or assistant. Avoid phrases like "How may I assist you?" or "Thank you for reaching out!".
3. Use natural, conversational phrasing ("Hey!", "Gotcha", "I'm out on a detail right now").
4. Always give the exact price from the knowledge base, then ask ONE question to lock in a booking slot or vehicle detail.
5. Help the customer choose a service and collect the vehicle type, preferred date, time, and service location needed to book.
"""
