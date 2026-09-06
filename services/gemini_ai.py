import os

from google import genai
from google.genai.types import HttpOptions

from config import HUMAN_SYSTEM_PROMPT

conversation_history: dict[str, list[dict[str, str]]] = {}
client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY"),
    http_options=HttpOptions(api_version="v1"),
)


def get_ai_reply(user_id: str, message: str) -> str:
    history = conversation_history.setdefault(user_id, [])
    history.append({"role": "user", "content": message})
    history_slice = history[-8:]
    transcript = "\n".join(
        f"{item['role'].title()}: {item['content']}" for item in history_slice
    )

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=f"{HUMAN_SYSTEM_PROMPT}\n\nConversation:\n{transcript}",
    )
    reply = response.text.strip()
    history.append({"role": "assistant", "content": reply})
    return reply