import os

import sentry_sdk
from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse

from config import SENTRY_DSN
from routes.telegram import router as telegram_router
from routes.twilio import router as twilio_router

sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=1.0)

app = FastAPI(title="AutoRecover AI Engine")

app.include_router(telegram_router)
app.include_router(twilio_router)


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return HTMLResponse("<h2>Dashboard file loading...</h2>")


@app.post("/api/chat")
async def web_sandbox_chat(Body: str = Form(...)):
    """Direct JSON endpoint for web dashboard sandbox"""
    from services.groq_ai import get_ai_reply

    reply = get_ai_reply(user_id="web_demo_user", message=Body)
    return {"reply": reply}
