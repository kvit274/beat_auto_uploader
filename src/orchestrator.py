import os
import random
import yaml
from dotenv import load_dotenv

from detect_audio_meta import detect_audio_meta

def pick_random_file(folder, exts=(".wav", ".mp3", ".flac")):
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(exts)]
    return random.choice(files) if files else None

def main(path):

    beat_path = pick_random_file(path)
    if not beat_path:
        raise FileNotFoundError("No beat files found.")
    
    bpm,key, confidence = detect_audio_meta(beat_path)

    print(f"Detected BPM={bpm}, Key={key} {confidence}")

if __name__ == "__main__":
    main("data/beats/don_toliver")
 

