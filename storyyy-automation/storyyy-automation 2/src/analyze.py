"""Turn YouTube Studio retention exports in retention/*.csv into reports/*.txt (uses vendor retention.py).
Name files like  my-video_45s.csv  (the _45s tells the tool the video length in seconds; optional)."""
import re, subprocess, sys
from common import ROOT

RET, REP = ROOT / "retention", ROOT / "reports"
TOOL = ROOT / "vendor" / "youtube-agent-skill" / "skills" / "yt-retention" / "retention.py"


def main():
    RET.mkdir(exist_ok=True); REP.mkdir(exist_ok=True)
    made = 0
    for csv in sorted(RET.glob("*.csv")):
        out = REP / (csv.stem + ".txt")
        if out.exists():
            continue
        cmd = [sys.executable, str(TOOL), str(csv)]
        m = re.search(r"_(\d+)s$", csv.stem)
        if m:
            cmd += ["--duration", m.group(1)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        out.write_text(f"Retention report for {csv.name}\n{res.stdout}{res.stderr}", encoding="utf-8")
        made += 1
        print("Wrote", out.name)
    print(f"{made} new report(s)")


if __name__ == "__main__":
    main()
