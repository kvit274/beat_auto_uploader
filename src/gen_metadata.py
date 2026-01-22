import os, json, re
import google.generativeai as genai
from dotenv import load_dotenv
import json
import jsonschema
import unicodedata
from typing import List

# Load .env and API key
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-flash-latest"
if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY in .env")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

response_schema = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "bs_tags": {"type": "ARRAY", "items": {"type": "STRING"}},
        "yt_tags": {"type": "ARRAY", "items": {"type": "STRING"}},
        "description": {"type": "STRING"},
        "tags": {"type": "ARRAY", "items": {"type": "STRING"}},
        "short_hashtags": {"type": "STRING"}
    },
    "required": ["title", "bs_tags", "yt_tags", "description", "tags", "short_hashtags"]
}



def limit_tags(tags: List[str], limit: int = 500) -> List[str]:
    total = 0
    selected = []
    for tag in tags:
        tag_length = len(tag.replace(",", ""))  # ignore commas
        if total + tag_length <= limit:
            selected.append(tag)
            total += tag_length
        else:
            break
    return selected


def call_gemini(prompt: str) -> str:
    """
    Calls the Gemini API and returns the model text output.
    """
    
    response = model.generate_content(
        prompt,
        generation_config={
            "response_mime_type": "application/json",
            "response_schema": response_schema
        })
    if not response.text:
        raise RuntimeError("Gemini returned empty response.")
    return response.text


def parse_json(text: str):
    """
    Extracts JSON object from text response and parses it.
    """
    try:
        match = re.search(r"\{.*\}", text, re.S)
        return json.loads(match.group(0)) if match else {}
    except Exception as e:
        print(f"⚠️ JSON parse error: {e}")
        return {}


def gen_metadata(artist: str, bpm: int, key: str,inst: str,email: str, tags):
    """
    Prompts Gemini to generate structured metadata for a given beat.
    """
    
    tags_str = ", ".join(tags)
   
    prompt = f"""
These are the most trending tags for {artist} right now: {tags_str}

Generate a JSON object using those tags with fields:
1) title: (≤60 chars) Example title: "[FREE] {artist} TYPE BEAT – 'ASTROVIBES'." (generate random name, all caps)
2) bs_tags: (3 relevant short tags for BeatStars)
3) yt_tags: (use supplied tags only, do NOT generate new ones; total char count excluding commas ≤500; make sure you are picking some tags with years)
4) description: Beat inspired by "Artist", Hope y'all like it!)
5) tags: list all trending tags provided
6) short_hashtags: (2–3 short relevant hashtags)
Only output valid JSON and nothing else.
"""
    raw = call_gemini(prompt)

    # Parse JSON safely
    try:
        data = json.loads(raw)
    except Exception as e:
        raise ValueError(f"Gemini returned invalid JSON: {e}\nRaw output:\n{raw}")

    # Validate against schema
    # try:
    #     jsonschema.validate(instance=data, schema=response_schema)
    # except jsonschema.ValidationError as e:
    #     raise ValueError(f"Schema validation failed: {e.message}")


    data = parse_json(raw)
    if not data:
        raise ValueError("Gemini did not generate any response")
    
    
    # Apply post-check (in case Gemini ignores it)
    data["yt_tags"] = limit_tags(data.get("yt_tags", []), 500)
    count = sum(len(tag.replace(",", "")) for tag in data["yt_tags"])
    print(f"YT tags length (excluding commas): {count}")

    print(json.dumps(data, indent=2, ensure_ascii=False))

    data["description"]+=f"\n\nUSAGE TERMS\nYou may use this beat only for writing lyrics and creating demo. If you want to use this beat commercially you can buy a lease at my beat store.\n\nDownload/Purchase: [beatstars_link]\n\nKey: {key}\nBpm: {bpm}\n\nInstagram: {inst}\nEmail: {email}\n\n"
    data["description"]+=f"\n\nTags\n{data['tags']}\n\n{data['short_hashtags']}"
    data["description"]=re.sub(r"[\[\]'\"]","",data["description"])
    
    with open("last_gen_metadata.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


if __name__ == "__main__":
    gen_metadata("Don Toliver", 148, "C#m","https://www.beatstars.com/kvit274","https://www.instagram.com/kvit_274_","kvit.beats2@gmail.com")



