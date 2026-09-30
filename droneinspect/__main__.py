import argparse
import os
import sys
from pathlib import Path

from .pipeline import Job, run


def main():
    ap = argparse.ArgumentParser(prog="droneinspect", description="Turn drone footage into an inspection report PDF.")
    ap.add_argument("source", type=Path, help="video file, image, or folder of images")
    ap.add_argument("--site", default="Unnamed site", help="site name for the report cover")
    ap.add_argument("--type", dest="profile", default="auto", choices=["auto", "oil_gas", "solar", "building", "civil", "generic"])
    ap.add_argument("--every", type=float, default=None, help="seconds between sampled frames (default: fit --max-frames)")
    ap.add_argument("--max-frames", type=int, default=30)
    ap.add_argument("--out", type=Path, default=Path("out"))
    ap.add_argument("--mock", action="store_true", help="no API calls; fake findings, for testing the pipeline")
    ap.add_argument("--mock-vision", action="store_true", help="fake image findings, real Jev triage")
    ap.add_argument("--observations", type=Path, help="JSON of pre-written observations instead of a vision API (see replay.py)")
    a = ap.parse_args()

    if not a.mock:
        needed = ["TYPESAFE_API_KEY"] + ([] if a.mock_vision or a.observations else ["ANTHROPIC_API_KEY"])
        missing = [k for k in needed if not os.environ.get(k)]
        if missing:
            sys.exit(f"Missing {', '.join(missing)}. Set them (see .env.example) or pass --mock.")

    out = a.out / a.source.stem
    pdf = run(Job(a.source, out, a.site, a.profile, a.every, a.max_frames, a.mock, a.mock_vision, a.observations))
    print(pdf)


if __name__ == "__main__":
    main()
