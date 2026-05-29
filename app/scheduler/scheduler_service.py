from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from pywebpush import webpush, WebPushException
import pickle
import json
import os
import requests
import google.auth
import google.auth.transport.requests
from google.oauth2 import service_account

from app.notifications.reminder_service import send_notification

scheduler = BackgroundScheduler()

REMINDER_MINUTES = [20, 15, 10, 5]
TRIGGER_WINDOW_SECONDS = 30
SENT_FILE = "sent_reminders.json"

VAPID_PRIVATE_KEY = "vapid_private.pem"
VAPID_EMAIL = "mailto:your@email.com"

FCM_DEVICE_TOKEN = "cFkIXitDRXysCXFDXwisFm:APA91bFBVCqQzRBy_rFex37jm3Ye4Igur4Xnp-WNu45aWfdHFZbQt22lfF80PqjwfbxptQuqp8LkyZbyV82r9gvylVbNtR0wzAKBvBuoQf_ugzEDbcc7Pbo"
SERVICE_ACCOUNT_FILE = "calendaralarm-eb0f7-bd033cdcaa99.json"
FCM_PROJECT_ID = "calendaralarm-eb0f7"

_due_reminders = []
cancelled_events = set()
_push_subscriptions = []


def set_push_subscriptions(subs: list):
    global _push_subscriptions
    _push_subscriptions = subs


def load_sent() -> set:
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_sent(sent: set):
    with open(SENT_FILE, "w") as f:
        json.dump(list(sent), f)


def get_calendar_service():
    with open("token.pkl", "rb") as token:
        credentials = pickle.load(token)
    return build("calendar", "v3", credentials=credentials)


def get_due_reminders():
    global _due_reminders
    reminders = _due_reminders.copy()
    _due_reminders = []
    return reminders


def cancel_event(event_id: str):
    cancelled_events.add(event_id)


def send_push(title: str, body: str):
    for sub in _push_subscriptions:
        try:
            webpush(
                subscription_info=sub,
                data=json.dumps({"title": title, "body": body}),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_EMAIL}
            )
        except WebPushException as e:
            print(f"  Push failed: {e}")


def send_fcm_notification(title: str, body: str):
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"]
        )
        credentials.refresh(google.auth.transport.requests.Request())
        access_token = credentials.token

        response = requests.post(
            f"https://fcm.googleapis.com/v1/projects/{FCM_PROJECT_ID}/messages:send",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "message": {
                    "token": FCM_DEVICE_TOKEN,
                    "data": {"title": title, "body": body}
                }
            }
        )
        print(f"  FCM response: {response.status_code} {response.text}")
    except Exception as e:
        print(f"  FCM failed: {e}")


def check_events():
    global _due_reminders
    print("Checking upcoming events...")

    service = get_calendar_service()
    now = datetime.now(timezone.utc).isoformat()

    events_result = service.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=10,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])
    current_time = datetime.now(timezone.utc)
    already_sent = load_sent()
    changed = False

    print(f"Found {len(events)} events")

    for event in events:
        title = event.get("summary", "Untitled Event")
        start = event["start"].get("dateTime", event["start"].get("date"))

        if "T" not in start:
            print(f"  Skipping all-day event: {title}")
            continue

        event_time = datetime.fromisoformat(
            start.replace("Z", "+00:00")
        ).astimezone(timezone.utc)

        minutes_until = round((event_time - current_time).total_seconds() / 60)
        print(f"Event: {title} — {minutes_until} mins away")

        for reminder_minute in REMINDER_MINUTES:
            reminder_id = (
                f"{title}-"
                f"{event_time.strftime('%Y-%m-%d-%H-%M')}-"
                f"{reminder_minute}"
            )

            target_time = event_time - timedelta(minutes=reminder_minute)
            seconds_from_target = abs((current_time - target_time).total_seconds())

            print(f"  checking {reminder_minute} min reminder — {round(seconds_from_target)}s from target — already sent: {reminder_id in already_sent}")

            if reminder_id in already_sent:
                continue

            if reminder_id in cancelled_events:
                continue

            if seconds_from_target <= TRIGGER_WINDOW_SECONDS:
                send_notification(
                    "Calendar Reminder",
                    f"{title} starts in {reminder_minute} minutes!"
                )
                send_push(
                    "Calendar Reminder",
                    f"{title} starts in {reminder_minute} minutes!"
                )
                send_fcm_notification(
                    "Calendar Reminder",
                    f"{title} starts in {reminder_minute} minutes!"
                )
                print(f"  Reminder sent for {title} ({reminder_minute} mins)")
                already_sent.add(reminder_id)
                changed = True

                _due_reminders.append({
                    "event_id": reminder_id,
                    "title": title,
                    "time": event_time.astimezone().strftime("%I:%M %p"),
                    "minutes_before": reminder_minute
                })

    if changed:
        save_sent(already_sent)


def start_scheduler():
    scheduler.add_job(check_events, "cron", second=0)
    scheduler.start()
