from groq import Groq

from config import GROQ_API_KEY, HUMAN_SYSTEM_PROMPT

conversation_history: dict[str, list[dict]] = {}


def get_ai_reply(user_id: str, message: str) -> str:
    if not GROQ_API_KEY:
        return "Error: GROQ_API_KEY environment variable is missing on Render."

    if user_id not in conversation_history:
        conversation_history[user_id] = [
            {"role": "system", "content": HUMAN_SYSTEM_PROMPT}
        ]

    conversation_history[user_id].append({"role": "user", "content": message})
    history_slice = [conversation_history[user_id][0]] + conversation_history[user_id][-8:]

    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=history_slice,
            temperature=0.65,
            max_tokens=150,
        )
        reply = response.choices[0].message.content.strip()
        conversation_history[user_id].append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"AI Error: {str(e)}"
