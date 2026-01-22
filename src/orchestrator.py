import os
import random
import yaml
from dotenv import load_dotenv
import json
import time

from detect_audio_meta import detect_audio_meta
from get_tags import get_trending_tags
from upload_to_beatstars import open_and_fill
from upload_to_youtube import upload_video
from rndm_select import *
from gen_metadata import gen_metadata
from gen_video import make_video

load_dotenv()
BEATSTARS_LINK=os.getenv("BEATSTARS_LINK")
INST_LINK=os.getenv("INST_LINK")
EMAIL=os.getenv("EMAIL")

# def main():
def main(chosen_beat_path,chosen_image_path,artist_name):

    # Check/refresh Google token before uploading to YouTube
    from google_auth_check import check_and_refresh_google_token
    try:
        creds = check_and_refresh_google_token()
        print("Google token valid and refreshed, ready to upload.")
    except Exception as e:
        print(f"Google token invalid: {e}")
        print("Please run google_auth_setup.py manually to re-authenticate.")
        return  # stop the orchestration safely

    # pick random beat
    # chosen_beat_path, chosen_beat, chosen_folder = pick_random_beat()
    # if not chosen_beat:
    #     raise ValueError("There are no beats to upload")
    
    # extract collabs
    collabs=[]
    # collabs = extract_collabs(chosen_beat)
    
    # pick random image
    # chosen_image_path,chosen_image = pick_random_picture(chosen_folder)
    # if not chosen_image:
    #     raise ValueError(f"There are no images to use for {chosen_folder} beats")
    
    # detect bpm and key of the beat
    bpm, key = detect_audio_meta(chosen_beat_path)
    # bpm = 136
    # key = "C# Minor"
    
    # get relevant tags:
    # tags = get_trending_tags(chosen_folder,50)
    tags = get_trending_tags(artist_name,50)

    # generate metadata
    # metaData = gen_metadata(chosen_folder, bpm, key,INST_LINK,EMAIL,tags)
    metaData = gen_metadata(artist_name, bpm, key,INST_LINK,EMAIL,tags)
    
    # with open("last_gen_metadata.json",'r',encoding="utf-8") as f:
    #     metaData = json.load(f)

    
    # upload to BeatStars
    MAX_ATTEMPTS = 3
    bs_link = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\nAttempt {attempt}/{MAX_ATTEMPTS} to upload on BeatStars...\n")
        try:
            bs_link = open_and_fill(chosen_beat_path,chosen_image_path,metaData["bs_tags"],collabs,metaData["title"])
            if bs_link and bs_link.startswith("https://bsta.rs/"):
                print(f"Upload successful on attempt {attempt}: {bs_link}")
                break
            else:
                print(f"[WARN] No BeatStars link captured on attempt {attempt}. Retrying...\n")
        except Exception as e:
            print(f"[ERROR] Upload attempt {attempt} failed: {e}\n")
            time.sleep(5)  # small delay before retrying

    if not bs_link:
        raise ValueError("All upload attempts failed. BeatStars link not captured.")
    else:
        print(f"Final BeatStars link: {bs_link}")
    
    # with open("last_published_link.txt",'r',encoding="utf-8") as f:
    #     bs_link = f.read().strip()
    
    # generate video
    video_path = make_video(chosen_image_path, chosen_beat_path)

    # upload to youtube
    metaData["description"] = metaData["description"].replace("beatstars_link",bs_link)
    yt_link=upload_video(video_path,metaData["title"],metaData["description"],metaData["yt_tags"],privacy_status="public")

    # delete files
    del_file(chosen_beat_path)
    del_file(chosen_image_path)
    del_file(video_path)
    return bs_link,yt_link
    
if __name__ == "__main__":
    main()
 

