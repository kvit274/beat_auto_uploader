import os, requests
from dotenv import load_dotenv, set_key
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

ENV_PATH = BASE_DIR / ".env"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
load_dotenv(ENV_PATH)

def check_and_refresh_google_token():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        raise RuntimeError("Missing credentials in .env — run google_auth_setup.py first.")

    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )

    if response.status_code != 200:
        print(f"⚠️ Invalid token: {response.json()}")
        raise RuntimeError("Refresh token invalid — re-run google_auth_setup.py manually.")

    data = response.json()
    new_token = data["access_token"]
    set_key(ENV_PATH, "GOOGLE_ACCESS_TOKEN", new_token)

    creds = Credentials(
        token=new_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds
