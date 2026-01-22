from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_check import check_and_refresh_google_token
from googleapiclient.discovery import build
import os
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# ===========================================
# Configuration
# ===========================================
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


CLIENT_SECRET_FILE = BASE_DIR / "secrets" / "client_secret.json"
VIDEO_PATH = BASE_DIR / "data" / "vids" / "test.mp4"
TOKEN_FILE = BASE_DIR / "secrets" / "token.pickle"

# ===========================================
# Authentication
# ===========================================
def get_authenticated_service():
    creds = check_and_refresh_google_token()
    youtube = build("youtube", "v3", credentials=creds)
    return youtube

import re
import unicodedata

def sanitize_youtube_tags(raw_tags):
    """
    Clean tags to satisfy YouTube API requirements:
    - Remove emojis, quotes, zero-width spaces, and non-ASCII chars
    - Limit each tag ≤ 30 chars
    - Total ≤ 500 characters
    - Deduplicate while preserving order
    """
    if not raw_tags:
        return []

    if isinstance(raw_tags, str):
        raw_tags = [t.strip() for t in raw_tags.split(",") if t.strip()]

    cleaned = []
    total_len = 0
    seen = set()

    for tag in raw_tags:
        tag = unicodedata.normalize("NFKD", tag)
        tag = re.sub(r"[\u200B-\u200F\u202A-\u202E]", "", tag)  # invisible chars
        tag = re.sub(r"[^A-Za-z0-9 _-]", "", tag)              # ASCII only
        tag = tag.strip()
        if not tag or len(tag) > 30 or tag in seen:
            continue
        if total_len + len(tag) > 500:
            break
        cleaned.append(tag)
        seen.add(tag)
        total_len += len(tag)
    return cleaned


# ===========================================
# Video Upload Function
# ===========================================
def upload_video(
    file_path,
    title,
    description,
    tags,
    category_id=10,
    privacy_status="private",
    default_language="en",
    default_audio_language="en",
    location_description="",
    location_latitude=None,
    location_longitude=None,
    recording_date=None,
    embeddable=True,
    license_type="youtube",
    public_stats_viewable=True,
    made_for_kids=False,
    notify_subscribers=True,
    publish_at=None,
):
    youtube = get_authenticated_service()

    tags = sanitize_youtube_tags(tags)

    # Build request body with all supported fields
    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "defaultLanguage": default_language,
            "defaultAudioLanguage": default_audio_language,
        },
        "status": {
            "privacyStatus": privacy_status,
            "embeddable": embeddable,
            "license": license_type,
            "publicStatsViewable": public_stats_viewable,
            "selfDeclaredMadeForKids": made_for_kids,
        },
        "recordingDetails": {},
    }

    if location_latitude and location_longitude:
        request_body["recordingDetails"]["location"] = {
            "latitude": location_latitude,
            "longitude": location_longitude,
        }
    if location_description:
        request_body["recordingDetails"]["locationDescription"] = location_description
    if recording_date:
        request_body["recordingDetails"]["recordingDate"] = recording_date
    if publish_at:
        request_body["status"]["publishAt"] = publish_at  # ISO8601 UTC string

    # Upload media
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)

    try:
        request = youtube.videos().insert(
            part="snippet,status,recordingDetails",
            body=request_body,
            media_body=media,
            notifySubscribers=notify_subscribers,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploading... {int(status.progress() * 100)}%")

        print("\nUpload complete!")
        print("Video ID:", response["id"])
        print("Watch here: https://youtu.be/" + response["id"])
        return f"https://youtu.be/" + response["id"]

    except HttpError as e:
        print(f"An error occurred: {e}")
        if e.resp.status in [403, 500, 503]:
            print("Retrying may help if quota or server errors.")
        raise


# ===========================================
# Example usage
# ===========================================
if __name__ == "__main__":
    # upload_video(
    #     file_path=VIDEO_PATH,
    #     title="C# Minor Beat - KVIT",
    #     description="Auto-uploaded beat in C# minor. Produced by KVIT.\n\nFollow for more!",
    #     tags=["trap", "beat", "kvit", "instrumental"],
    #     category_id="10",  # Music
    #     privacy_status="private",
    #     default_language="en",
    #     default_audio_language="en",
    #     location_description="Cork, Ireland",
    #     location_latitude=51.8969,
    #     location_longitude=-8.4863,
    #     recording_date=datetime.datetime.utcnow().isoformat("T") + "Z",
    #     embeddable=True,
    #     license_type="youtube",
    #     public_stats_viewable=True,
    #     made_for_kids=False,
    #     notify_subscribers=False,
    #     publish_at="2025-11-05T10:00:00Z",  # Scheduled publish (UTC)
    # )
    get_authenticated_service()
