import os, subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

VIDEO_DIR = BASE_DIR / "data" / "vids"


def make_video(img, audio, fps=30, codec="libx264", crf=18, ab="320k"):
    """
    Creates a 16:9 YouTube-ready video (e.g. 1920x1080) using an image as background
    and centers the original image without resizing or stretching.
    Black bars fill the rest of the frame if needed.
    """
    out_path = os.path.join(VIDEO_DIR, f"{os.path.splitext(os.path.basename(audio))[0]}.mp4")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # Target YouTube resolution
    width, height = 1920, 1080

    # ffmpeg filter explanation:
    # - scale: ensures image fits inside target size without changing aspect ratio
    # - pad: adds black bars around to reach 16:9
    vf_filter = (
        f"scale=w=min(iw*min({width}/iw\\,{height}/ih)\\,{width}):"
        f"h=min(ih*min({width}/iw\\,{height}/ih)\\,{height}),"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-framerate", str(fps),
        "-i", img,
        "-i", audio,
        "-vf", vf_filter,
        "-c:v", codec,
        "-tune", "stillimage",
        "-crf", str(crf),
        "-c:a", "aac",
        "-b:a", ab,
        "-shortest",
        out_path
    ]

    subprocess.run(cmd, check=True)
    return out_path



if __name__ == "__main__":
    BEAT_PATH = "/Users/kvit/Documents/beat_auto_uploader/data/beats/don_toliver/ALLIANCE_135_VIRTHY_KVIT.mp3"
    IMAGE_PATH = "/Users/kvit/Documents/beat_auto_uploader/data/images/don_toliver/don.jpg"
    video_out = os.path.join("/Users/kvit/Documents/beat_auto_uploader/data/vids", f"{os.path.splitext(os.path.basename(BEAT_PATH))[0]}.mp4")
    make_video(IMAGE_PATH, BEAT_PATH)

