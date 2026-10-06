import json, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUEUE = ROOT / "queue"
QUEUE.mkdir(exist_ok=True)


def load_item(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_item(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def all_items():
    return sorted(QUEUE.glob("*.json"))


def duration(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path)])
    return float(out)
