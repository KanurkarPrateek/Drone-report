"""Turn drone footage (or a folder of stills) into a list of frames to inspect."""

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_EDGE = 1568  # the vision model downsizes anything larger, so don't upload it


@dataclass
class Frame:
    index: int
    path: Path
    timestamp_s: float | None  # None for stills


def probe_duration(video: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video)],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(out.stdout)["format"]["duration"])


def extract_frames(source: Path, out_dir: Path, every_s: float | None = None, max_frames: int = 30) -> tuple[list[Frame], dict]:
    """Sample frames evenly across the video.

    If `every_s` is not given, the interval is chosen so the whole clip fits in
    `max_frames` frames (at least one frame every 2 s for short clips).
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    if source.is_dir() or source.suffix.lower() in IMAGE_EXTS:
        return _stills(source, out_dir, max_frames)

    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required: brew install ffmpeg")

    duration = probe_duration(source)
    if every_s is None:
        every_s = max(2.0, duration / max_frames)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(source),
         "-vf", f"fps=1/{every_s},scale='min({MAX_EDGE},iw)':-2",
         "-frames:v", str(max_frames), "-q:v", "3",
         str(out_dir / "frame_%04d.jpg")],
        check=True,
    )
    paths = sorted(out_dir.glob("frame_*.jpg"))
    frames = [Frame(i, p, round(i * every_s, 1)) for i, p in enumerate(paths)]
    return frames, {"duration_s": round(duration, 1), "interval_s": round(every_s, 2), "kind": "video"}


def _stills(source: Path, out_dir: Path, max_frames: int) -> tuple[list[Frame], dict]:
    from PIL import Image

    files = [source] if source.is_file() else sorted(p for p in source.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    frames = []
    for i, f in enumerate(files[:max_frames]):
        img = Image.open(f).convert("RGB")
        img.thumbnail((MAX_EDGE, MAX_EDGE))
        dest = out_dir / f"frame_{i + 1:04d}.jpg"
        img.save(dest, quality=90)
        frames.append(Frame(i, dest, None))
    return frames, {"duration_s": None, "interval_s": None, "kind": "images"}
