from googleapiclient.discovery import build
from dotenv import load_dotenv
from collections import Counter
from datetime import datetime
import os
import json
import re

load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


def normalize_tag(tag: str) -> str:
    """Lowercase, remove symbols, keep year, clean spacing."""
    tag = tag.lower().strip()
    tag = re.sub(r"[\[\]\(\)\|#]", "", tag)  # remove brackets, pipes, hashtags
    tag = re.sub(r"\s+", " ", tag)           # collapse spaces
    return tag.strip()


def fetch_videos(youtube, query, order="relevance", max_results=15):
    """Return (video_id, publishedAt) tuples for a query."""
    search = youtube.search().list(
        q=query,
        part="id,snippet",
        maxResults=max_results,
        type="video",
        order=order
    )
    res = search.execute()
    videos = []
    for item in res["items"]:
        vid = item["id"]["videoId"]
        date = item["snippet"]["publishedAt"]
        videos.append((vid, date))
    return videos


def fetch_tags(youtube, videos, artist):
    """Return Counter of tags weighted by recency."""
    tag_counter = Counter()
    now = datetime.now()

    for vid, pub in videos:
        video = youtube.videos().list(part="snippet", id=vid).execute()
        if not video["items"]:
            continue
        snippet = video["items"][0]["snippet"]
        tags = snippet.get("tags", [])
        pub_dt = datetime.strptime(pub, "%Y-%m-%dT%H:%M:%SZ")
        age_days = (now - pub_dt).days
        recency_weight = max(0.5, 1.5 - (age_days / 90))  # bias newer videos

        seen = set()
        for t in tags:
            norm = normalize_tag(t)
            if not norm:
                continue
            if any(word in norm for word in ["beat", artist.lower(), "trap", "instrumental", "type"]):
                seen.add(norm)
        for s in seen:
            tag_counter[s] += recency_weight

    return tag_counter


def get_trending_tags(artist: str, top_n: int = 40):
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    query = f"{artist} type beat"

    # Fetch both relevance- and date-sorted videos
    vids_relevance = fetch_videos(youtube, query, order="relevance", max_results=15)
    vids_recent = fetch_videos(youtube, query, order="date", max_results=15)
    all_videos = vids_relevance + vids_recent

    tag_counter = fetch_tags(youtube, all_videos, artist)

    ranked = [t for t, _ in tag_counter.most_common(top_n)]
    print(f"✅ {len(tag_counter)} unique tags fetched (top {len(ranked)} returned).")
    return ranked


if __name__ == "__main__":
    artist = "Don Toliver"
    tags = get_trending_tags(artist)

    os.makedirs("cache/tags", exist_ok=True)
    out_path = f"cache/tags/{artist.lower().replace(' ', '_')}.json"
    with open(out_path, "w") as f:
        json.dump(tags, f, indent=2)

    print("\n🔥 Top trending tags:")
    for t in tags:
        print("-", t)
