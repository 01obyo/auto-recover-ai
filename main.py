import os

import sentry_sdk
from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse

from config import SENTRY_DSN
from routes.telegram import router as telegram_router
from routes.twilio import router as twilio_router
from routes.auth import router as auth_router  # <-- Added new Auth Router import

sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=1.0)

app = FastAPI(title="AutoRecover AI Engine")

app.include_router(telegram_router)
app.include_router(twilio_router)
app.include_router(auth_router)  # <-- Registered Auth Router here


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return HTMLResponse("<h2>Dashboard file loading...</h2>")


@app.post("/api/chat")
async def web_sandbox_chat(Body: str = Form(...)):
    """Direct JSON endpoint for web dashboard sandbox"""
    from services.gemini_ai import get_ai_reply

    reply = get_ai_reply(user_id="web_demo_user", message=Body)
    return {"reply": reply}


@app.get("/test-ui", response_class=HTMLResponse)
async def test_ui():
    return """
    <html>
        <head>
            <title>AutoRecover AI Test</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-[#051F20] text-white flex items-center justify-center h-screen">
            <div class="bg-[#0B2B26] p-8 rounded-xl shadow-lg w-96 border border-[#235347]">
                <h1 class="text-xl font-bold mb-4 text-[#8EB69B]">AutoRecover AI Tester</h1>
                <form action="/twilio/webhook" method="POST" class="space-y-4">
                    <div>
                        <label class="block text-sm mb-1">Caller Number</label>
                        <input type="text" name="From" value="+1234567890" class="w-full p-2 rounded bg-[#163832] border border-[#235347] text-white">
                    </div>
                    <div>
                        <label class="block text-sm mb-1">Message / Missed Call Note</label>
                        <textarea name="Body" class="w-full p-2 rounded bg-[#163832] border border-[#235347] text-white">Hello, I missed your call.</textarea>
                    </div>
                    <button type="submit" class="w-full bg-[#235347] hover:bg-[#8EB69B] hover:text-[#051F20] py-2 rounded font-bold transition">Simulate Webhook</button>
                </form>
            </div>
        </body>
    </html>
    """
