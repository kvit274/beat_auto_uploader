from playwright.sync_api import sync_playwright
import json

OAUTH_URL = (
    "https://oauth.beatstars.com/login"
    "?app=WEB_STUDIO&version=3.14.0"
    "&origin=https://studio.beatstars.com"
    "&send_callback=true&t=dark-theme"
)

def manual_auth_and_save():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("\n[INFO] Opening BeatStars login page...")
        page.goto(OAUTH_URL, wait_until="load")

        print(
            "\nPlease log in manually in the opened browser window."
            "\nOnce you reach your BeatStars Studio dashboard "
            "(https://studio.beatstars.com), return here and press Enter."
        )
        input("\nPress Enter when finished login: ")

        # Save the full browser storage (cookies, localStorage, sessionStorage)
        context.storage_state(path="beatstars_session.json")
        print("Session saved to beatstars_session.json")

        browser.close()

if __name__ == "__main__":
    manual_auth_and_save()