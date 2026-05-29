from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.auth.auth_service import get_auth_url, fetch_and_save_user, save_fcm_token
from app.scheduler.scheduler_service import start_scheduler, scheduler, get_due_reminders, cancel_event, set_push_subscriptions
import os

push_subscriptions = []

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.get("/login")
def login(request: Request, fcm_token: str = ""):
    redirect_uri = f"{BASE_URL}/auth/callback"
    auth_url = get_auth_url(redirect_uri, fcm_token)
    return RedirectResponse(auth_url)


@app.get("/auth/callback")
def auth_callback(code: str, state: str = "", request: Request = None):
    redirect_uri = f"{BASE_URL}/auth/callback"
    email = fetch_and_save_user(code, redirect_uri, fcm_token=state)
    return HTMLResponse(f"""
        <html>
        <body style="font-family: sans-serif; text-align: center; padding: 50px; background: #1a1a2e; color: white;">
            <h1>✅ Logged in as {email}</h1>
            <p>Your calendar is now synced!</p>
            <p>You will receive alarm notifications for your events.</p>
            <p>You can close this tab now.</p>
        </body>
        </html>
    """)


@app.post("/api/register-fcm")
async def register_fcm(request: Request):
    data = await request.json()
    email = data.get("email")
    fcm_token = data.get("fcm_token")
    success = save_fcm_token(email, fcm_token)
    return {"ok": success}


@app.get("/api/due-reminders")
def due_reminders():
    return {"reminders": get_due_reminders()}


@app.get("/alarm")
def alarm_page():
    return FileResponse("static/index.html")


@app.post("/api/subscribe")
async def subscribe(request: Request):
    data = await request.json()
    if data not in push_subscriptions:
        push_subscriptions.append(data)
    set_push_subscriptions(push_subscriptions)
    return {"ok": True}


@app.post("/api/cancel-reminders")
async def cancel_reminders(request: Request):
    data = await request.json()
    cancel_event(data["event_id"])
    return {"ok": True}
