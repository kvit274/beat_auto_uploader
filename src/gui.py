import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QLineEdit, QStackedWidget, QMessageBox
from dotenv import load_dotenv, set_key
import subprocess
from playwright.sync_api import sync_playwright
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from orchestrator import main as orchestrator_main  # Import the main function from orchestrator.py

# Load environment variables
load_dotenv()

# Check if the required credentials exist in the .env file
def check_credentials():
    return all([
        os.getenv("BEATSTARS_LINK"),
        os.getenv("INST_LINK"),
        os.getenv("EMAIL"),
        os.getenv("YOUTUBE_API_KEY"),
        os.path.exists("beatstars_session.json")
    ])

# Save credentials to .env
def save_api_keys(beatstars_link, instagram_link, email, youtube_api_key):
    set_key(".env", "BEATSTARS_LINK", beatstars_link)
    set_key(".env", "INST_LINK", instagram_link)
    set_key(".env", "EMAIL", email)
    set_key(".env", "YOUTUBE_API_KEY", youtube_api_key)

# Authenticate to Google via OAuth2 (for YouTube)
def authenticate_youtube():
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secret.json', ['https://www.googleapis.com/auth/youtube.upload']
    )
    credentials = flow.run_local_server(port=0)
    youtube = build('youtube', 'v3', credentials=credentials)
    return youtube

# Authenticate to BeatStars (check if session exists)
def authenticate_beatstars():
    if not os.path.exists("beatstars_session.json"):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            OAUTH_URL = (
                "https://oauth.beatstars.com/login"
                "?app=WEB_STUDIO&version=3.14.0"
                "&origin=https://studio.beatstars.com"
                "&send_callback=true&t=dark-theme"
            )
            page.goto(OAUTH_URL, wait_until="load")

            QMessageBox.information(None, "Login", "Please log in to BeatStars and then return here.")
            input("Press Enter after logging into BeatStars...")

            # Save the session to be reused later
            context.storage_state(path="beatstars_session.json")
            print("BeatStars session saved to beatstars_session.json")
            browser.close()

# Upload function using orchestrator.py
def upload_files(beat_file, image_file, stems_file, artist_name, upload_time):
    print(f"Uploading: Beat: {beat_file}, Image: {image_file}, Stems: {stems_file}")
    
    # Call the orchestrator.py main function to process the upload
    bs_link,yt_link = orchestrator_main(beat_file, image_file, artist_name)  # Pass the chosen beat, image, and artist name
    return bs_link,yt_link

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Beat Upload Automation")
        self.setGeometry(200, 200, 600, 400)
        self.layout = QVBoxLayout()

        # Stacked widget for page navigation
        self.pages = QStackedWidget(self)

        # Page 1: Credentials Page
        self.page_credentials = QWidget()
        self.layout_credentials = QVBoxLayout()

        self.link_beatstars_input = QLineEdit(self)
        self.link_beatstars_input.setPlaceholderText("Enter your BeatStars link (e.g., https://www.beatstars.com/kvit274)")
        self.layout_credentials.addWidget(self.link_beatstars_input)

        self.link_instagram_input = QLineEdit(self)
        self.link_instagram_input.setPlaceholderText("Enter your Instagram link (e.g., https://www.instagram.com/kvit_274_)")
        self.layout_credentials.addWidget(self.link_instagram_input)

        self.email_input = QLineEdit(self)
        self.email_input.setPlaceholderText("Enter your Email (e.g., kvit.beats2@gmail.com)")
        self.layout_credentials.addWidget(self.email_input)

        self.yt_api_key_input = QLineEdit(self)
        self.yt_api_key_input.setPlaceholderText("Enter your YouTube API Key")
        self.layout_credentials.addWidget(self.yt_api_key_input)

        self.save_button = QPushButton("Save Credentials", self)
        self.save_button.clicked.connect(self.save_credentials)
        self.layout_credentials.addWidget(self.save_button)

        self.page_credentials.setLayout(self.layout_credentials)

        # Page 2: Upload Page
        self.page_upload = QWidget()
        self.layout_upload = QVBoxLayout()

        self.artist_name_input = QLineEdit(self)
        self.artist_name_input.setPlaceholderText("Enter Artist Name")
        self.layout_upload.addWidget(self.artist_name_input)

        self.upload_button_beat = QPushButton("Upload Beat", self)
        self.upload_button_beat.clicked.connect(self.upload_beat)
        self.layout_upload.addWidget(self.upload_button_beat)

        self.upload_button_image = QPushButton("Upload Image", self)
        self.upload_button_image.clicked.connect(self.upload_image)
        self.layout_upload.addWidget(self.upload_button_image)

        self.selected_stems = None
        self.upload_button_stems = QPushButton("Upload Stems", self)
        self.upload_button_stems.clicked.connect(self.upload_stems)
        self.layout_upload.addWidget(self.upload_button_stems)

        self.upload_button_start = QPushButton("Start Upload", self)
        self.upload_button_start.clicked.connect(self.start_upload)
        self.layout_upload.addWidget(self.upload_button_start)

        self.page_upload.setLayout(self.layout_upload)

        # Page 3: Log Page
        self.page_log = QWidget()
        self.layout_log = QVBoxLayout()

        self.log_text = QLabel("Logs will be shown here.")
        self.layout_log.addWidget(self.log_text)

        self.page_log.setLayout(self.layout_log)

        # Add pages to the stacked widget
        self.pages.addWidget(self.page_credentials)
        self.pages.addWidget(self.page_upload)
        self.pages.addWidget(self.page_log)

        # Set the stacked widget as the layout
        self.layout.addWidget(self.pages)
        self.setLayout(self.layout)

        # Start on the credentials page if credentials are not saved
        if not check_credentials():
            self.pages.setCurrentIndex(0)
        else:
            self.pages.setCurrentIndex(1)

    def save_credentials(self):
        # Save credentials in .env
        beatstars_link = self.link_beatstars_input.text()
        instagram_link = self.link_instagram_input.text()
        email = self.email_input.text()
        yt_api_key = self.yt_api_key_input.text()

        if beatstars_link and instagram_link and email and yt_api_key:
            save_api_keys(beatstars_link, instagram_link, email, yt_api_key)
            QMessageBox.information(self, "Credentials Saved", "Credentials have been saved successfully.")
            self.pages.setCurrentIndex(1)  # Go to the upload page
        else:
            QMessageBox.warning(self, "Input Error", "Please provide all required information.")

    def upload_beat(self):
        # Open file dialog to select a beat
        beat_file, _ = QFileDialog.getOpenFileName(self, "Select Beat File", "", "Audio Files (*.mp3 *.wav)")
        if beat_file:
            self.selected_beat = beat_file
            QMessageBox.information(self, "Beat Selected", f"Selected beat: {beat_file}")

    def upload_image(self):
        # Open file dialog to select an image
        image_file, _ = QFileDialog.getOpenFileName(self, "Select Image File", "", "Image Files (*.jpg *.png)")
        if image_file:
            self.selected_image = image_file
            QMessageBox.information(self, "Image Selected", f"Selected image: {image_file}")

    def upload_stems(self):
        # Open file dialog to select stems
        stems_file, _ = QFileDialog.getOpenFileName(self, "Select Stems File", "", "Zip Files (*.zip)")
        if stems_file:
            self.selected_stems = stems_file
            QMessageBox.information(self, "Stems Selected", f"Selected stems: {stems_file}")

    def start_upload(self):
        # Get the artist name
        artist_name = self.artist_name_input.text()

        # Check if all files are selected
        if not hasattr(self, 'selected_beat') or not hasattr(self, 'selected_image'):
            QMessageBox.warning(self, "Missing Files", "Please select both a beat and an image.")
            return

        # Start upload process
        beat_link, yt_link = upload_files(self.selected_beat, self.selected_image, self.selected_stems, artist_name, "2025-11-05T10:00:00Z")
        self.log_text.setText(f"Upload Complete!\n\nBeatStars: {beat_link}\nYouTube: {yt_link}")

# Main entry point
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())
