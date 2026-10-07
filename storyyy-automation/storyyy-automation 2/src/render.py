"""Turn a queue item into a 1080x1920 MP4: edge-tts voice + Pexels stock clips + burned-in captions."""
import asyncio, os, pathlib, random, subprocess, textwrap, requests
import edge_tts
from common import ROOT, duration

VOICE = os.environ.get("TTS_VOICE", "en-US-GuyNeural")
PEXELS = os.environ.get("PEXELS_API_KEY", "").strip()
PIXABAY = os.environ.get("PIXABAY_API_KEY", "").strip()
if not (PEXELS or PIXABAY):
    raise SystemExit("Set PEXELS_API_KEY or PIXABAY_API_KEY (at least one).")
W, H = 1080, 1920
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FALLBACK_QUERIES = ["calm sky", "city night", "forest light", "ocean waves"]


def sh(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


async def _tts(text, out):
    await edge_tts.Communicate(text, VOICE, rate="-5%").save(str(out))


def _pexels(q, used):
    r = requests.get("https://api.pexels.com/videos/search",
                     headers={"Authorization": PEXELS},
                     params={"query": q, "orientation": "portrait", "per_page": 10}, timeout=60)
    r.raise_for_status()
    vids = [v for v in r.json().get("videos", []) if v["id"] not in used]
    random.shuffle(vids)
    for v in vids[:6]:
        files = [f for f in v["video_files"]
                 if f.get("file_type") == "video/mp4" and f.get("width") and f.get("height")
                 and f["height"] >= f["width"]]
        if files:
            f = min(files, key=lambda f: abs(f["width"] - 1080))
            return ("pexels", v["id"]), f["link"]
    return None


def _pixabay(q, used):
    # Pixabay has no portrait filter; clips are usually landscape and get center-cropped to 9:16.
    r = requests.get("https://pixabay.com/api/videos/",
                     params={"key": PIXABAY, "q": q[:90], "per_page": 20, "safesearch": "true"}, timeout=60)
    r.raise_for_status()
    hits = [h for h in r.json().get("hits", []) if ("pixabay", h["id"]) not in used]
    random.shuffle(hits)
    for h in hits[:6]:
        sizes = [v for v in h.get("videos", {}).values() if v.get("url") and v.get("height")]
        if sizes:
            best = max(sizes, key=lambda v: v["height"])  # biggest = least blurry after the crop
            return ("pixabay", h["id"]), best["url"]
    return None


def fetch_clip(query, dest, used):
    providers = ([_pexels] if PEXELS else []) + ([_pixabay] if PIXABAY else [])
    for q in [query] + FALLBACK_QUERIES:
        for provider in providers:
            try:
                found = provider(q, used)
            except requests.RequestException as e:
                print("Clip search failed:", provider.__name__, e)
                continue
            if found:
                key, link = found
                dest.write_bytes(requests.get(link, timeout=180).content)
                used.add(key)
                return dest
    raise RuntimeError(f"No clip found for {query!r}")


def render_segment(clip, audio, text, dur, out, txt_file):
    txt_file.write_text(textwrap.fill(text, 22), encoding="utf-8")
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,"
          f"drawtext=fontfile={FONT}:textfile={txt_file}:expansion=none:fontcolor=white:fontsize=72:"
          f"line_spacing=12:borderw=6:bordercolor=black:x=(w-text_w)/2:y=h*0.62,format=yuv420p")
    sh(["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(clip), "-i", str(audio),
        "-t", f"{dur + 0.25:.2f}", "-vf", vf, "-af", "apad=pad_dur=0.25",
        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", str(out)])


def render(item, stem):
    tmp = ROOT / "tmp" / stem
    tmp.mkdir(parents=True, exist_ok=True)
    (ROOT / "out").mkdir(exist_ok=True)
    used, segs = set(), []
    for i, line in enumerate(item["lines"]):
        audio = tmp / f"a{i}.mp3"
        asyncio.run(_tts(line["text"], audio))
        clip = fetch_clip(line["visual"], tmp / f"c{i}.mp4", used)
        seg = tmp / f"s{i}.mp4"
        render_segment(clip, audio, line["text"], duration(audio), seg, tmp / f"t{i}.txt")
        segs.append(seg)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{s}'\n" for s in segs))
    joined = tmp / "joined.mp4"
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)])
    final = ROOT / "out" / f"{stem}.mp4"
    music = ROOT / "assets" / "music.mp3"  # optional: drop a royalty-free track here
    if music.exists():
        sh(["ffmpeg", "-y", "-i", str(joined), "-stream_loop", "-1", "-i", str(music),
            "-filter_complex", "[1:a]volume=0.08[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest", str(final)])
    else:
        joined.replace(final)
    return final
