import os
import random
import re
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent



# base directory containing your folders
BEATS_DIR = BASE_DIR / "data" / "beats"
IMG_DIR = BASE_DIR / "data" / "images"
COLLABS_JSON = BASE_DIR / "data" / "collaborators" / "collaborators.json"

import os
import random

def pick_random_beat():
    AUDIO_EXTS = ('.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.aiff', '.wma')

    def is_audio_file(path: str) -> bool:
        """Return True if path is a valid audio file (by extension, not hidden)."""
        return (
            os.path.isfile(path)
            and path.lower().endswith(AUDIO_EXTS)
            and not os.path.basename(path).startswith('.')
        )

    non_empty_folders = []
    for folder_name in os.listdir(BEATS_DIR):
        folder_path = os.path.join(BEATS_DIR, folder_name)
        if not os.path.isdir(folder_path):
            continue

        # find all valid audio files in this folder
        audio_files = [
            f for f in os.listdir(folder_path)
            if is_audio_file(os.path.join(folder_path, f))
        ]

        if audio_files:  # only count folders with real audio files
            non_empty_folders.append((folder_name, audio_files))

    if not non_empty_folders:
        return None, None, None  # no folders with audio files

    # pick random folder and random audio file inside
    chosen_folder, audio_files = random.choice(non_empty_folders)
    chosen_beat = random.choice(audio_files)
    beat_path = os.path.join(BEATS_DIR, chosen_folder, chosen_beat)

    return beat_path, chosen_beat, chosen_folder


import os
import random

def pick_random_picture(chosen_folder):
    IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff')

    def is_image_file(path: str) -> bool:
        """Return True if path is a valid image file (by extension, not hidden)."""
        return (
            os.path.isfile(path)
            and path.lower().endswith(IMAGE_EXTS)
            and not os.path.basename(path).startswith('.')
        )

    folder_path = os.path.join(IMG_DIR, chosen_folder)
    if not os.path.isdir(folder_path):
        return None, None

    # collect all valid images
    images = [
        f for f in os.listdir(folder_path)
        if is_image_file(os.path.join(folder_path, f))
    ]

    if not images:
        return None, None  # no valid images in this folder

    chosen_image = random.choice(images)
    image_path = os.path.join(folder_path, chosen_image)

    return image_path, chosen_image


def del_file(file_path):
    # delete selected file
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"{os.path.basename(file_path)} successfully deleted")

def extract_collabs(filename):
    name, _ = os.path.splitext(filename)
    parts = name.split()

    bpm_index = None

    for i, part in enumerate(parts):
        token = part.lower()

        # Case 1: token itself is a BPM (like "148" or "148bpm" or "bpm148")
        if token.isdigit() or re.match(r'^(bpm)?\d+(bpm)?$', token):
            bpm_index = i
            break

        # Case 2: token is "bpm" and next token is a number (handles "bpm 148")
        if token == "bpm" and i + 1 < len(parts) and re.match(r'^\d+$', parts[i + 1]):
            bpm_index = i + 1  # we mark the number as the BPM index
            break

    if bpm_index is None:
        print(f"No BPM found in: {filename}")
        return []

    # Everything after BPM are producers
    producers_raw = parts[bpm_index + 1:]

    # Clean names: remove @, _, leading digits
    cleaned = [re.sub(r'^[@_\d]+', '', p).lower() for p in producers_raw if p.strip()]

    with open(COLLABS_JSON,"r",encoding="utf-8") as f:
        data=json.load(f)

    # Known producers (keys + values)
    known = set([k.lower() for k in data.keys()] + [v.lower() for v in data.values()])

    collabs = [p for p in cleaned if p in known]

    return collabs