from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.auth.auth_service import get_auth_url, fetch_calendar_events
from app.notifications.reminder_engine import check_upcoming_events
from app.scheduler.scheduler_service import start_scheduler, scheduler, get_due_reminders, cancel_event, set_push_subscriptions

push_subscriptions = []
cancelled_events = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def home():
    return {"message": "my ai agent is alive"}


@app.get("/login")
def login():
    auth_url = get_auth_url()
    return RedirectResponse(auth_url)


@app.get("/auth/callback")
def auth_callback(code: str):
    events = fetch_calendar_events(code)
    cleaned_events = []
    for event in events:
        cleaned_events.append({
            "title": event.get("summary"),
            "start": event.get("start"),
            "end": event.get("end")
        })
    return {
        "message": "Google login successful",
        "events": cleaned_events
    }


@app.get("/check-reminders")
def reminders(code: str):
    events = fetch_calendar_events(code)
    upcoming = check_upcoming_events(events)
    return {"upcoming_events": upcoming}


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
