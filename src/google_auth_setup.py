import os
import json
import requests
from dotenv import load_dotenv, set_key
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

ENV_PATH = BASE_DIR / ".env"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

load_dotenv(ENV_PATH)

# Ensure client_secret.json exists
CLIENT_SECRET_FILE = "client_secret.json"
if not os.path.exists(CLIENT_SECRET_FILE):
    raise FileNotFoundError("Missing client_secret.json file.")

def save_env_var(key, value):
    """Save or update a key=value pair inside .env"""
    set_key(ENV_PATH, key, value)
    os.environ[key] = value

def validate_refresh_token(refresh_token, client_id, client_secret):
    """Check if the stored refresh token is still valid."""
    try:
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
        if response.status_code == 200:
            access_token = response.json().get("access_token")
            if access_token:
                print("Refresh token is valid.")
                save_env_var("GOOGLE_ACCESS_TOKEN", access_token)
                return True
        else:
            print("Token validation failed:", response.json())
    except Exception as e:
        print("Validation error:", e)
    return False


def authenticate_and_store():
    """Run OAuth flow, get refresh token, and store credentials in .env"""
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    refresh_token = creds.refresh_token
    access_token = creds.token
    client_id = creds.client_id
    client_secret = creds.client_secret

    print("\nAuthentication successful.")
    print("Saving credentials to .env ...")

    save_env_var("GOOGLE_CLIENT_ID", client_id)
    save_env_var("GOOGLE_CLIENT_SECRET", client_secret)
    save_env_var("GOOGLE_REFRESH_TOKEN", refresh_token)
    save_env_var("GOOGLE_ACCESS_TOKEN", access_token)

    print("Saved to .env successfully.")


def main():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")

    if client_id and client_secret and refresh_token:
        print("🔎 Found existing credentials in .env, validating...")
        if validate_refresh_token(refresh_token, client_id, client_secret):
            print("Existing credentials are valid — nothing to do.")
            return
        else:
            print("Stored refresh token invalid — re-authenticating.")
            authenticate_and_store()
    else:
        print("No valid credentials found — starting authentication.")
        authenticate_and_store()


if __name__ == "__main__":
    main()
