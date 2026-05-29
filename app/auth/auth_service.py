import pickle
import json
import os

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]

USERS_FILE = "users.json"


def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)


def make_flow(redirect_uri):
    return Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )


def get_auth_url(redirect_uri):
    flow = make_flow(redirect_uri)
    auth_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent'
    )
    return auth_url


def fetch_and_save_user(code, redirect_uri):
    flow = make_flow(redirect_uri)
    flow.fetch_token(code=code)
    credentials = flow.credentials

    service = build('oauth2', 'v2', credentials=credentials)
    user_info = service.userinfo().get().execute()
    email = user_info['email']

    users = load_users()
    users[email] = {
        "email": email,
        "token": pickle.dumps(credentials).hex(),
        "fcm_token": users.get(email, {}).get("fcm_token", None)
    }
    save_users(users)

    return email


def save_fcm_token(email: str, fcm_token: str):
    users = load_users()
    if email in users:
        users[email]["fcm_token"] = fcm_token
        save_users(users)
        return True
    return False


def get_all_users():
    return load_users()
