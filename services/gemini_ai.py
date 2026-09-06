from google import genai

from config import GEMINI_API_KEY, HUMAN_SYSTEM_PROMPT

conversation_history: dict[str, list[dict[str, str]]] = {}
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


def get_ai_reply(user_id: str, message: str) -> str:
    if client is None:
        raise RuntimeError("GEMINI_API_KEY environment variable is not configured")

    history = conversation_history.setdefault(user_id, [])
    history.append({"role": "user", "content": message})
    history_slice = history[-8:]
    transcript = "\n".join(
        f"{item['role'].title()}: {item['content']}" for item in history_slice
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{HUMAN_SYSTEM_PROMPT}\n\nConversation:\n{transcript}",
    )
    reply = response.text.strip()
    history.append({"role": "assistant", "content": reply})
    return reply