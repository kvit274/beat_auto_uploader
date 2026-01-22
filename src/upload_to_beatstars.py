from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from pathlib import Path
import os, re, time, random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# ===== CONFIG =====

SESSION_FILE = BASE_DIR / "secrets" / "beatstars_session.json"
STEMS_PATH = BASE_DIR / "data" / "stems"
# ===================


# ─────────────────────────────────────────────
# Utility Functions
# ─────────────────────────────────────────────

def wait_for_any(page, selectors, timeout_ms=120_000, check_interval=500):
    """Wait until any of the selectors appears."""
    for _ in range(int(timeout_ms / check_interval)):
        for sel in selectors:
            if page.locator(sel).count() and page.locator(sel).first.is_visible():
                return sel
        page.wait_for_timeout(check_interval)
    raise PlaywrightTimeoutError(f"None of {selectors} appeared within {timeout_ms} ms.")


def wait_until_disappears(page, selectors, timeout_ms=300_000, check_interval=500):
    """Wait until all given selectors disappear or are hidden."""
    for _ in range(int(timeout_ms / check_interval)):
        if all(page.locator(sel).count() == 0 or not page.locator(sel).first.is_visible() for sel in selectors):
            return True
        page.wait_for_timeout(check_interval)
    raise PlaywrightTimeoutError(f"{selectors} did not disappear within {timeout_ms} ms.")


def retry_action(func, retries=3, delay=1500):
    """Retry an action a few times before failing."""
    for attempt in range(retries):
        try:
            return func()
        except Exception as e:
            print(f"[WARN] Attempt {attempt+1}/{retries} failed: {e}")
            time.sleep(delay / 1000)
    raise RuntimeError(f"Action failed after {retries} retries.")


def wait_changes_saved(page, timeout_ms=180_000):
    """Wait until 'Changes Saved' message appears after metadata processing."""
    try:
        wait_until_disappears(page, ["text=/Metadata Processing/i"], timeout_ms=timeout_ms)
    except Exception:
        pass
    page.locator("text=/Changes Saved/i").wait_for(state="visible", timeout=timeout_ms)


def attach_via_uppy_in_current_modal(page, file_path):
    """Attach a file inside the open Uppy modal."""
    page.wait_for_selector("text=/Upload file/i", timeout=20_000)
    try:
        page.get_by_text("browse files", exact=False).click()
    except Exception:
        pass

    for _ in range(3):
        inputs = page.query_selector_all('input.uppy-Dashboard-input[type="file"]')
        if inputs:
            break
        page.wait_for_timeout(500)

    if not inputs:
        raise RuntimeError("Uppy input not found.")

    file_input = inputs[0]
    page.evaluate(
        """el => { el.removeAttribute('hidden');
                   el.style.display='block';
                   el.style.visibility='visible';
                   el.style.opacity=1; }""",
        file_input
    )
    file_input.set_input_files(file_path)

def check_allowed_limits(title,tags):
    TITLE_LIMIT = 60
    TAGS_LIMIT = 3
    if len(title) > TITLE_LIMIT:
        title = title.replace("[FREE] ","")
    if len(tags) > TAGS_LIMIT:
        tags = [tags[i] for i in range(TAGS_LIMIT)]
    return title,tags


# ─────────────────────────────────────────────
# Main Upload Function
# ─────────────────────────────────────────────

def open_and_fill(beat_path, image_path, tags, collaborators, title):

    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    folder_name = os.path.basename(os.path.dirname(beat_path))
    file_basename = os.path.splitext(os.path.basename(beat_path))[0]
    stems_path = os.path.join(STEMS_PATH, folder_name, f"{file_basename}.zip")

    # check limits
    title,tags = check_allowed_limits(title,tags)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(
            storage_state=SESSION_FILE,
            permissions=["clipboard-read", "clipboard-write"]
        )
        page = context.new_page()

        # 1️⃣ Go to Dashboard -> Create Track
        page.goto("https://studio.beatstars.com/dashboard", wait_until="load")
        retry_action(lambda: page.get_by_role("button", name="Create").click())
        page.wait_for_timeout(400)
        retry_action(lambda: page.get_by_role("menuitem", name="Create Track").click())
        page.wait_for_url("**/content/tracks/uploaded**", timeout=60_000)

        # Close update popup if visible
        try:
            if page.locator("button:has-text('Dismiss')").is_visible():
                page.locator("button:has-text('Dismiss')").click()
        except Exception:
            pass

        # 2️⃣ Upload MP3 / audio file
        print("[INFO] Uploading audio...")
        attach_via_uppy_in_current_modal(page, beat_path)
        print("[INFO] Audio selected. Waiting for upload to start...")

        try:
            # Wait for the 'Master Track (Untagged)' section to show 'Uploading' text
            master_section = page.locator("text=/Master Track/i").first
            page.wait_for_function(
                """section => section && section.innerText.includes('Uploading')""",
                arg=master_section,
                timeout=90_000
            )
            print("[INFO] Upload started — waiting for completion...")

            # Wait until that same section no longer contains 'Uploading'
            page.wait_for_function(
                """section => !section.innerText.includes('Uploading')""",
                arg=master_section,
                timeout=600_000
            )

            # Wait until BeatStars shows metadata or next step
            page.wait_for_selector("text=/Metadata|Preview Track|Stem Files/i", timeout=60_000)
            print("[INFO] Audio uploaded successfully.")
        except PlaywrightTimeoutError:
            print("[WARN] Upload progress not detected — continuing cautiously.")


        # 6️⃣ Upload Artwork (Browse → Save → Upload 1 file)
        try:
            print("[INFO] Uploading artwork...")

            # Open Edit → Upload file
            page.get_by_role("button", name=re.compile("Edit", re.I)).first.click()
            page.wait_for_timeout(300)
            page.get_by_role("menuitem", name=re.compile("Upload file", re.I)).first.click()

            # Wait for Uppy dashboard
            page.wait_for_selector(".uppy-Dashboard-inner", timeout=30_000)

            # --- Attach file into Uppy ---
            for _ in range(12):
                inputs = page.query_selector_all('input.uppy-Dashboard-input[type="file"]')
                if inputs:
                    break
                page.wait_for_timeout(250)
            if not inputs:
                raise RuntimeError("Uppy file input not found.")
            file_input = inputs[0]
            page.evaluate(
                """el => { el.removeAttribute('hidden');
                          el.style.display='block';
                          el.style.visibility='visible';
                          el.style.opacity=1; }""",
                file_input
            )
            file_input.set_input_files(image_path)
            print("[INFO] File attached, waiting for cropping modal...")

            # --- Cropping modal (click Save) ---
            # Wait until cropping editor appears
            page.wait_for_selector(".uppy-DashboardContent-save", timeout=60_000)
            save_button = page.locator("button.uppy-DashboardContent-save")
            save_button.wait_for(state="visible", timeout=20_000)

            # Click Save with retries
            for attempt in range(4):
                try:
                    save_button.scroll_into_view_if_needed()
                    save_button.click(timeout=2000)
                    print("[INFO] Cropping modal: real 'Save' clicked.")
                    break
                except Exception as e:
                    print(f"[WARN] Cropping save click attempt {attempt+1} failed: {e}")
                    page.wait_for_timeout(500)
            else:
                raise RuntimeError("Failed to click 'Save' in cropping modal.")

            # Wait until that Save button disappears
            page.wait_for_function(
                "() => document.querySelectorAll('.uppy-DashboardContent-save').length===0",
                timeout=60_000
            )
            print("[INFO] Cropping modal closed, returning to Uppy dashboard.")


            # --- Click Upload 1 file ---
            upload_btn = page.get_by_role("button", name=re.compile(r"Upload 1 file", re.I)).first
            upload_btn.wait_for(state="visible", timeout=30_000)
            upload_btn.click()
            print("[INFO] 'Upload 1 file' clicked.")

            # 🕒 Wait for BeatStars upload panel (bottom-right) to appear & disappear
            try:
                print("[INFO] Waiting for BeatStars bottom-right uploader panel...")

                # Phase 1: wait until panel appears (Uploading / Uploaded text)
                panel_appeared = False
                for _ in range(60):  # up to ~30 seconds
                    if page.locator("text=/Uploading|Uploaded all files/i").count() > 0:
                        panel_appeared = True
                        break
                    page.wait_for_timeout(500)
                if panel_appeared:
                    print("[INFO] Upload panel appeared — waiting for it to finish.")
                else:
                    print("[WARN] Upload panel never appeared; continuing to monitor disappearance anyway.")

                # Phase 2: wait until it disappears completely
                page.wait_for_function(
                    """() => {
                        const nodes = Array.from(document.querySelectorAll('*'));
                        return !nodes.some(e => /Uploading|Uploaded all files/i.test(e.textContent || ''));
                    }""",
                    timeout=360_000  # up to 6 minutes
                )
                print("[INFO] Upload panel disappeared — upload fully processed.")
            except Exception as e:
                print(f"[WARN] Upload panel wait timed out or failed: {e}")


            # Wait until Uppy modal closes
            page.wait_for_function(
                "() => document.querySelectorAll('.uppy-Dashboard-inner').length===0",
                timeout=120_000
            )
            print("[INFO] Uppy modal closed.")

            # Wait for BeatStars to persist
            try:
                page.locator("text=/Changes Saved/i").wait_for(state="visible", timeout=120_000)
            except Exception:
                pass

            print("Artwork uploaded and saved successfully.")

        except Exception as e:
            page.screenshot(path="debug_artwork_fail.png", full_page=True)
            print(f"[ERROR] Artwork upload failed: {e}")



        # 3️⃣ Fill Title
        try:
            title_input = page.locator('input[placeholder*="Title" i]').first
            title_input.fill(title)
            print("[INFO] Title filled.")
        except Exception:
            print("[WARN] Title input not found.")

        # 4️⃣ Fill Tags
        try:
            for i, tag in enumerate(tags, start=1):
                input_selectors = [
                    "input[placeholder*='tag']",
                    "input[aria-label*='tag']",
                    "input[placeholder*='Tag']",
                    "input[aria-label*='Tag']",
                ]
                tag_input = next((page.locator(sel).last for sel in input_selectors if page.locator(sel).count()), None)
                if not tag_input:
                    raise RuntimeError("No tag input found.")
                tag_input.wait_for(state="visible", timeout=20_000)
                tag_input.fill(tag)
                tag_input.press("Enter")
                page.wait_for_timeout(200)
                print(f"[INFO] Added tag {i}: {tag}")
        except Exception as e:
            print(f"[WARN] Could not fill tags: {e}")

        # 5️⃣ Autofill Metadata
        try:
            autofill_btn = page.get_by_text(re.compile("Autofill.*Metadata", re.I))
            if not autofill_btn.count():
                autofill_btn = page.locator("button:has-text('Autofill')")
            autofill_btn.first.click()
            print("[INFO] Autofill metadata clicked.")
            wait_changes_saved(page)
        except Exception:
            print("[WARN] Autofill button not found.")



        # 7️⃣ Upload Stems (if exists)
        try:
            stem_path = Path(stems_path)
            if stem_path.exists():
                print(f"[INFO] Uploading stems: {stem_path.name}")
                stem_section = page.locator("section:has-text('Stem Files')")
                stem_section.wait_for(state="visible", timeout=30_000)
                stem_section.locator("button:has-text('Add')").first.click()
                attach_via_uppy_in_current_modal(page, str(stem_path))
                wait_for_any(page, ["text=/Processing/i", "text=/Uploading/i"], 180_000)
                wait_until_disappears(page, ["text=/Processing/i", "text=/Uploading/i"], 600_000)
                print("[INFO] Stems uploaded successfully.")
            else:
                print(f"[WARN] Stem file not found at {stem_path}. Skipping.")
        except Exception as e:
            print(f"[WARN] Stems upload failed: {e}")

        # 8️⃣ Add Collaborators
        try:
            collabs = collaborators if isinstance(collaborators, list) else [collaborators]
            collabs = [c.strip() for c in collabs if c.strip()]
            for collab in collabs:
                print(f"[INFO] Adding collaborator: {collab}")
                if not page.locator('input[placeholder*="Artist"]').count():
                    page.get_by_text("Add collaborator", exact=False).click()
                    page.wait_for_timeout(800)
                artist_inputs = page.locator('input[placeholder*="Artist"]')
                empty_field = next((artist_inputs.nth(i) for i in range(artist_inputs.count()) if not artist_inputs.nth(i).input_value().strip()), None)
                (empty_field or artist_inputs.last).fill(collab)
                wait_changes_saved(page)
                print(f"[INFO] Collaborator '{collab}' added.")
        except Exception as e:
            print(f"[WARN] Collaborator step failed: {e}")

        # 9️⃣ Publish Track
        try:
            wait_changes_saved(page)
            publish_btn = page.locator("button:has-text('Publish Track')").first
            publish_btn.wait_for(state="visible", timeout=180_000)
            page.evaluate("const o=document.querySelector('#survey_1049305');if(o)o.style.display='none';")
            publish_btn.click(force=True)
            print("Publish button clicked.")
        except Exception as e:
            print(f"[WARN] Publish button failed: {e}")

        # 🔟 Extract BeatStars Link
        # 8️⃣ Extract BeatStars link after publish (via "View all links" modal)
        try:
            print("[INFO] Waiting for BeatStars shortlink modal...")

            # Wait for initial modal after publish
            page.wait_for_selector("text=Share your CONTENT with the world!", timeout=60_000)

            # Click "View all links"
            view_links_btn = page.get_by_text("View all links", exact=False)
            if view_links_btn.count():
                view_links_btn.first.click()
                print("[INFO] Opened 'View all links' modal.")
            else:
                print("[WARN] 'View all links' button not found. Attempting fallback.")

            # Wait for "Marketplace short URL" section
            page.wait_for_selector("text=Marketplace short URL", timeout=20_000)

            # Click "Copy link" beside short URL
            copy_btn = page.locator("button:has-text('Copy link')").first
            copy_btn.click()
            print("[INFO] Clicked 'Copy link' for short URL.")

            # Wait briefly for clipboard update
            page.wait_for_timeout(1000)

            # Try reading from clipboard in page context
            beat_link = page.evaluate("navigator.clipboard.readText()")

            if beat_link and beat_link.startswith("https://bsta.rs/"):
                print(f"BeatStars shortlink copied: {beat_link}")
                with open("last_published_link.txt", "w") as f:
                    f.write(beat_link)
                return beat_link
            else:
                print("[WARN] Clipboard read empty or invalid; falling back to DOM extraction...")

                # Fallback: extract value from the short URL input field
                short_input = page.locator("input[value^='https://bsta.rs/']").first
                if short_input.count():
                    beat_link = short_input.get_attribute("value")
                    print(f"Fallback shortlink found: {beat_link}")
                    with open("last_published_link.txt", "w") as f:
                        f.write(beat_link)
                else:
                    beat_link = None
                    print("[WARN] BeatStars link not found in modal.")

                return beat_link

        except Exception as e:
            print(f"[WARN] Could not extract BeatStars link: {e}")



if __name__ == "__main__":
    from rndm_select import pick_random_beat,pick_random_picture
    beat_path, chosen_beat, chosen_folder = pick_random_beat()
    image_path, _ = pick_random_picture(chosen_folder)
    tags = ["cool"]
    collaborators = []
    title = "Test"

    MAX_ATTEMPTS = 3
    beatstars_link = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\nAttempt {attempt}/{MAX_ATTEMPTS} to upload on BeatStars...\n")
        try:
            beatstars_link = open_and_fill(beat_path, image_path, tags, collaborators, title)
            if beatstars_link and beatstars_link.startswith("https://bsta.rs/"):
                print(f"Upload successful on attempt {attempt}: {beatstars_link}")
                break
            else:
                print(f"[WARN] No BeatStars link captured on attempt {attempt}. Retrying...\n")
        except Exception as e:
            print(f"[ERROR] Upload attempt {attempt} failed: {e}\n")
            time.sleep(5)  # small delay before retrying

    if not beatstars_link:
        print("All upload attempts failed. BeatStars link not captured.")
    else:
        print(f"Final BeatStars link: {beatstars_link}")

    
