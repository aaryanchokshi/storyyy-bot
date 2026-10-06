"""Create ONE new story draft in queue/ (approved=false). You review it, then flip approved to true."""
import datetime, json, os, random, requests
from common import QUEUE, all_items, load_item, save_item

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")  # change if Google retires it
KEY = os.environ["GEMINI_API_KEY"]

THEMES = [
    "failing and trying again", "a small act of kindness that changed everything",
    "starting late in life", "choosing discipline over motivation",
    "a mentor's unexpected advice", "losing something and finding strength",
    "ignoring doubters", "patience and slow progress", "a childhood lesson remembered as an adult",
]
STRUCTURES = [
    "a story with a surprising twist ending", "a letter written to your future self",
    "a first-person confession", "a short fable with animals",
    "a slice-of-life moment told in the present tense", "a conversation between two people",
]

PROMPT = """You write short ORIGINAL stories for a YouTube Shorts channel called "Storyyy Timee".
Write ONE new story.
- Theme: {theme}
- Form: {structure}
- 110-140 words total (about 45-55 seconds when read aloud).
- Concrete details (names, places, one surprising specific). No generic quote lists, no cliches like "you got this".
- Do not copy existing stories, speeches or quotes.
- Split into 10-14 narration lines, each under 14 words.
- For each line give a 1-3 word stock-footage search term ("visual"): concrete and filmable, e.g. "rainy window", "runner sunrise".
- Do NOT reuse these earlier titles: {past}
Return ONLY JSON:
{{"title": "<=70 chars, no hashtags", "description": "2 sentences", "tags": ["up to 8"], "lines": [{{"text": "...", "visual": "..."}}]}}"""


def main():
    past = [load_item(p).get("title", "") for p in all_items()][-40:]
    prompt = PROMPT.format(theme=random.choice(THEMES), structure=random.choice(STRUCTURES), past=past or "none")
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        params={"key": KEY},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"responseMimeType": "application/json", "temperature": 1.0}},
        timeout=120)
    r.raise_for_status()
    data = json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
    lines = data.get("lines") or []
    assert lines and all(l.get("text") and l.get("visual") for l in lines), "Bad script from model"
    item = {"title": data["title"], "description": data.get("description", ""),
            "tags": data.get("tags", [])[:8], "lines": lines,
            "approved": False, "published": False, "youtube_id": None}
    name = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S") + ".json"
    save_item(QUEUE / name, item)
    print("Created", name, "-", item["title"])


if __name__ == "__main__":
    main()
