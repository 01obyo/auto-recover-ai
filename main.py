import os
from fastapi import FastAPI, Form, Response
from fastapi.responses import HTMLResponse, FileResponse
from twilio.twiml.messaging_response import MessagingResponse
from groq import Groq

app = FastAPI(title="AutoRecover AI Engine")

conversation_history = {}

HUMAN_SYSTEM_PROMPT = """
You are Alex, the sole owner/receptionist at Apex Mobile Auto Detailing. A customer missed your call after reaching out.

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
"""

def get_ai_reply(user_id: str, message: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return "Error: GROQ_API_KEY environment variable is missing on Render."

    if user_id not in conversation_history:
        conversation_history[user_id] = [{"role": "system", "content": HUMAN_SYSTEM_PROMPT}]

    conversation_history[user_id].append({"role": "user", "content": message})
    history_slice = [conversation_history[user_id][0]] + conversation_history[user_id][-8:]

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=history_slice,
            temperature=0.65,
            max_tokens=150
        )
        reply = response.choices[0].message.content.strip()
        conversation_history[user_id].append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"AI Error: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return HTMLResponse("<h2>Dashboard file loading...</h2>")

@app.post("/api/chat")
async def web_sandbox_chat(Body: str = Form(...)):
    """Direct JSON endpoint for web dashboard sandbox"""
    reply = get_ai_reply(user_id="web_demo_user", message=Body)
    return {"reply": reply}

@app.post("/sms")
async def handle_incoming_sms(From: str = Form(...), Body: str = Form(...)):
    """TwiML XML endpoint for live Twilio SMS webhook"""
    reply = get_ai_reply(user_id=From, message=Body)
    twiml = MessagingResponse()
    twiml.message(reply)
    return Response(content=str(twiml), media_type="application/xml")

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    
    # Extract chat ID and text from Telegram's payload
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"].get("text", "")
        
        # Pass user_text to Groq and send response back to Telegram...
        
    return {"status": "ok"}
import os
import httpx
from fastapi import Request

@app.post("/webhook/telegram")
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
                    json={"chat_id": chat_id, "text": ai_response}
                )
                
    return {"status": "ok"}


