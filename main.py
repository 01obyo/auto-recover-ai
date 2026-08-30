import os
from fastapi import FastAPI, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
from groq import Groq

app = FastAPI(title="AutoRecover AI Engine")

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

conversation_history = {}

HUMAN_SYSTEM_PROMPT = """
You are Alex, the sole owner/receptionist at Apex Mobile Auto Detailing. A customer just tried calling your mobile line while you were on a job.

HUMAN TEXTING RULES (CRITICAL):
1. Sound like a real person texting from a smartphone. Keep messages brief (1 to 3 short sentences max).
2. NEVER sound like an assistant or bot. No "How may I assist you today?" or "Thank you for reaching out!".
3. Use casual, natural phrasing ("Hey!", "Gotcha", "No problem", "I'm out on a detail right now").
4. Always ask ONE question at a time so the back-and-forth feels natural.
5. If they want a price or booking, ask for their vehicle type or preferred day.
6. If they want an in-person estimate before paying, agree immediately and set a 10-minute slot.
"""

@app.post("/sms")
async def handle_incoming_sms(From: str = Form(...), Body: str = Form(...)):
    if From not in conversation_history:
        conversation_history[From] = [
            {"role": "system", "content": HUMAN_SYSTEM_PROMPT}
        ]

    conversation_history[From].append({"role": "user", "content": Body})
    history_slice = [conversation_history[From][0]] + conversation_history[From][-8:]

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=history_slice,
        temperature=0.65,
        max_tokens=150
    )

    human_reply = response.choices[0].message.content.strip()
    conversation_history[From].append({"role": "assistant", "content": human_reply})

    twiml = MessagingResponse()
    twiml.message(human_reply)

    return Response(content=str(twiml), media_type="application/xml")
