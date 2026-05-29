import pickle

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar"
]

flow = Flow.from_client_secrets_file(
    'credentials.json',
    scopes=SCOPES,
    redirect_uri='http://localhost:8000/auth/callback'
)


def get_auth_url():
    auth_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent'
    )
    return auth_url


def fetch_calendar_events(code):
    flow.fetch_token(code=code)

    credentials = flow.credentials

    with open("token.pkl", "wb") as token:
        pickle.dump(credentials, token)

    service = build('calendar', 'v3', credentials=credentials)

    events_result = service.events().list(
        calendarId='primary',
        maxResults=10,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])

    return events
