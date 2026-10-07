"""Create ONE new story draft in queue/ (approved=false).

Merged pipeline:
  1. Gemini writes 7 candidate opening hooks, each built on a DIFFERENT formula from the 21 in
     vendor/youtube-agent-skill/skills/yt-script/hooks.json
  2. hookscore.py (vendor, MIT) scores every hook; the best becomes narration line 1
  3. Gemini writes the rest of the story + 3 title options; title.py lints the titles; best wins
  4. Lessons from your own retention reports (reports/*.txt) are added to the prompt
You review the draft, optionally swap the hook/title from "review", and set approved=true.
"""
import datetime, json, os, random, sys, time, requests
from common import ROOT, QUEUE, all_items, load_item, save_item

_V = ROOT / "vendor" / "youtube-agent-skill" / "skills"
sys.path[:0] = [str(_V / "yt-script"), str(_V / "yt-package")]
import hookscore            # noqa: E402  (vendor, MIT)
import title as titlelint   # noqa: E402  (vendor, MIT)

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")  # change if Google retires it
N_HOOKS = 7

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

HOOK_PROMPT = """You write opening lines for short spoken stories on a YouTube Shorts channel called "Storyyy Timee".

CHANNEL VOICE (follow it):
{channel}

Today's theme: {theme}
Today's story form: {structure}

Write {n} DIFFERENT opening lines (9-24 words each, the first thing the narrator says). Each one must use a DIFFERENT hook formula from this list, adapted to storytelling:
{formulas}

A good story hook opens a gap the listener needs closed. Include a concrete detail (number, name, place, object). Speak to the listener or drop them into a specific moment. Do NOT start with a greeting or "Once upon a time". Do NOT reveal the ending.
Return ONLY JSON: {{"hooks": [{{"formula": "<formula name>", "text": "<opening line>"}}]}}"""

STORY_PROMPT = """You write short ORIGINAL stories for a YouTube Shorts channel called "Storyyy Timee".

CHANNEL VOICE (follow it):
{channel}

Theme: {theme}
Form: {structure}

The story MUST begin with exactly this opening line as narration line 1:
"{hook}"

Rules:
- 110-140 words total (about 45-55 seconds read aloud). Continue naturally from the opening line.
- Concrete details; a surprising turn; a quiet, memorable ending. No cliches, no copied quotes.
- 10-14 narration lines, each under 14 words (line 1 may be longer).
- For each line give a 1-3 word stock-footage search term ("visual"): concrete and filmable, e.g. "rainy window", "runner sunrise".
- Give 3 different title options, each under 60 characters, specific, no hashtags, at most one ALL-CAPS word.
- Do NOT reuse these earlier titles: {past}

LESSONS FROM THIS CHANNEL'S OWN RETENTION REPORTS (apply them if any):
{lessons}

Return ONLY JSON:
{{"titles": ["..."], "description": "2 sentences", "tags": ["up to 8"], "lines": [{{"text": "...", "visual": "..."}}]}}"""


def gemini_json(prompt, temperature=1.0):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    last = None
    for attempt in range(3):
        try:
            r = requests.post(
                url, params={"key": os.environ["GEMINI_API_KEY"]},
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"responseMimeType": "application/json", "temperature": temperature}},
                timeout=120)
            r.raise_for_status()
            return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
        except Exception as e:  # network, quota, bad JSON
            last = e
            print(f"Gemini attempt {attempt + 1} failed: {e}")
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Gemini failed 3 times: {last}")


def read_channel():
    p = ROOT / "config" / "channel.md"
    return p.read_text(encoding="utf-8") if p.exists() else "Warm, simple, original short stories."


def read_lessons():
    files = sorted((ROOT / "reports").glob("*.txt"))[-3:]
    if not files:
        return "none yet"
    return "\n\n".join(f.read_text(encoding="utf-8")[:1200] for f in files)


def pick_hook(theme, structure, channel):
    formulas = random.sample(hookscore.FORMULAS, N_HOOKS)
    ftxt = "\n".join(f"- {f['name']}: {f['shape']} (example: {f['example']})" for f in formulas)
    data = gemini_json(HOOK_PROMPT.format(channel=channel, theme=theme, structure=structure,
                                          n=N_HOOKS, formulas=ftxt))
    cands = []
    for h in data.get("hooks", []):
        text = (h.get("text") or "").strip()
        if not text:
            continue
        parts, verdict, _, _ = hookscore.score(text)
        weakest = min(parts, key=parts.get)
        cands.append({"text": text, "formula": h.get("formula", "?"), "score": verdict,
                      "band": hookscore.band(verdict), "weakest": weakest, "fix": hookscore.FIX[weakest]})
    if not cands:
        raise RuntimeError("Model returned no usable hooks")
    cands.sort(key=lambda c: -c["score"])
    return cands


def pick_title(options):
    rows = [titlelint.check(t) for t in options if t and t.strip()]
    if not rows:
        raise RuntimeError("Model returned no titles")
    rows.sort(key=lambda r: -r["score"])
    return rows


def main():
    channel = read_channel()
    theme, structure = random.choice(THEMES), random.choice(STRUCTURES)
    past = [load_item(p).get("title", "") for p in all_items()][-40:]

    hooks = pick_hook(theme, structure, channel)
    best_hook = hooks[0]
    print(f"Hook: [{best_hook['band']} {best_hook['score']}] {best_hook['formula']}: {best_hook['text']}")

    data = gemini_json(STORY_PROMPT.format(channel=channel, theme=theme, structure=structure,
                                           hook=best_hook["text"], past=past or "none",
                                           lessons=read_lessons()))
    lines = data.get("lines") or []
    assert lines and all(l.get("text") and l.get("visual") for l in lines), "Bad script from model"
    lines[0]["text"] = best_hook["text"]  # guarantee the scored hook is what gets spoken

    titles = pick_title(data.get("titles") or [])
    item = {
        "title": titles[0]["title"], "description": data.get("description", ""),
        "tags": data.get("tags", [])[:8], "lines": lines,
        "approved": False, "published": False, "youtube_id": None,
        "review": {
            "how_to_swap": "To use another hook, paste its text into lines[0].text. To use another title, paste it into title.",
            "theme": theme, "form": structure,
            "hook_chosen": best_hook,
            "hook_candidates": hooks,
            "title_candidates": [{"title": r["title"], "score": r["score"],
                                  "issues": [m for _, m in r["issues"]]} for r in titles],
        },
    }
    name = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S") + ".json"
    save_item(QUEUE / name, item)
    print("Created", name, "-", item["title"])


if __name__ == "__main__":
    main()
