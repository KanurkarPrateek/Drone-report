"""Footage in, PDF out.

  frames  ->  Claude (see: what is wrong, where)  ->  Jev (judge: category, severity,
  action, hazard, real-or-not)  ->  code (drop false alarms, merge duplicates, set
  priority)  ->  Claude (executive summary)  ->  PDF
"""

import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

from .frames import extract_frames
from .profiles import PROFILES, SEVERITY_NAMES, action_label, repair_guidance
from .triage import THRESHOLDS

PRIORITY_COLORS = {"P1": (220, 38, 38), "P2": (234, 138, 0), "P3": (37, 99, 235)}


@dataclass
class Job:
    source: Path
    out_dir: Path
    site: str = "Unnamed site"
    profile: str = "auto"               # oil_gas | solar | generic | auto
    every_s: float | None = None
    max_frames: int = 30
    mock: bool = False                  # fake vision AND fake Jev
    mock_vision: bool = False           # fake vision, real Jev (test Jev without a vision key)
    observations: Path | None = None    # pre-written observations (replay.py) instead of a vision API
    anthropic_key: str | None = None    # None -> ANTHROPIC_API_KEY from the environment
    typesafe_key: str | None = None     # None -> TYPESAFE_API_KEY from the environment
    vision_model: str | None = None     # None -> vision.MODEL
    jev_model: str | None = None        # None -> triage.MODEL
    log: Callable[[str], None] = print
    # stage(name, fraction_done): drives the progress bar in the web UI
    stage: Callable[[str, float], None] = lambda name, frac: None

    def __repr__(self):  # never print keys
        return f"Job(site={self.site!r}, source={self.source.name!r}, profile={self.profile!r})"


def run(job: Job) -> Path:
    t0 = time.time()
    job.out_dir.mkdir(parents=True, exist_ok=True)

    if job.observations:
        from .replay import ReplayInspector
        inspector = ReplayInspector(job.observations)
    elif job.mock or job.mock_vision:
        from .mock import MockInspector, MockTriage
        inspector = MockInspector("oil_gas" if job.profile == "auto" else job.profile)
    else:
        from .vision import MODEL as VISION_MODEL, Inspector
        inspector = Inspector(model=job.vision_model or VISION_MODEL, api_key=job.anthropic_key)

    job.stage("frames", 0.0)
    job.log("Extracting frames from footage...")
    frames, meta = extract_frames(job.source, job.out_dir / "frames", job.every_s, job.max_frames)
    if not frames:
        raise RuntimeError("No frames could be read from the upload.")
    job.log(f"Got {len(frames)} frames.")

    profile = job.profile
    if profile == "auto":
        pick = [frames[0].path, frames[len(frames) // 2].path, frames[-1].path]
        guess = inspector.guess_asset(pick)
        profile = guess.asset_type
        job.log(f"Detected site type: {PROFILES[profile]['name']}")

    # 1. See: every frame through the vision model, in parallel.
    job.stage("see", 0.0)
    job.log(f"Inspecting {len(frames)} frames with the vision model...")
    analyses, frame_errors = {}, []

    def see(frame):
        try:
            return frame, inspector.analyse(frame.path, profile, frame.timestamp_s), None
        except Exception as e:  # one bad frame must not sink the report
            return frame, None, f"{type(e).__name__}: {e}"[:200]

    with ThreadPoolExecutor(max_workers=4) as pool:
        for n, (frame, analysis, err) in enumerate(pool.map(see, frames), 1):
            if err:
                frame_errors.append({"frame": frame.index, "error": err})
            else:
                analyses[frame.index] = analysis
            job.stage("see", n / len(frames))
            if n % 5 == 0 or n == len(frames):
                job.log(f"  {n}/{len(frames)} frames inspected")

    raw = []
    for frame in frames:
        a = analyses.get(frame.index)
        for obs in (a.observations if a else []):
            raw.append({"frame": frame, "analysis": a, "obs": obs.model_dump()})
    job.log(f"Vision model reported {len(raw)} observations.")

    # 2. Judge: every observation through Jev.
    if job.mock:
        triage = MockTriage(profile)
    else:
        from .triage import MODEL as JEV_MODEL, Triage
        triage = Triage(profile, model=job.jev_model or JEV_MODEL, api_key=job.typesafe_key)
    job.stage("judge", 0.0)
    job.log(f"Triaging {len(raw)} observations with Jev...")

    def judge(item):
        ctx = {"timestamp_s": item["frame"].timestamp_s, "scene": item["analysis"].scene,
               "image_quality": item["analysis"].image_quality, "is_thermal": item["analysis"].is_thermal}
        obs = {k: v for k, v in item["obs"].items() if k != "bbox"}
        try:
            return {**item, "judgment": triage.judge(obs, ctx)}
        except Exception as e:
            job.log(f"  Jev call failed ({type(e).__name__}); keeping finding unscored")
            return {**item, "judgment": _unscored(e)}

    with ThreadPoolExecutor(max_workers=8) as pool:
        judged = list(pool.map(judge, raw))

    job.stage("judge", 0.7)
    # 3. Decide: code applies the thresholds.
    kept = [j for j in judged if j["judgment"]["genuine"] >= THRESHOLDS["drop_if_genuine_below"]]
    dropped = len(judged) - len(kept)
    findings = _merge_duplicates(kept, getattr(triage, "same_defect", None), job.log)
    # Round severity so tiny run-to-run wobble in Jev's scores can't reshuffle finding IDs.
    findings.sort(key=lambda f: (f["judgment"]["priority"], -round(f["judgment"]["severity"], 1), f["frame"].index))
    job.log(f"{len(findings)} findings after removing {dropped} likely false alarms and merging repeats.")

    # 4. Evidence images + repair guidance.
    fig_dir = job.out_dir / "findings"
    fig_dir.mkdir(exist_ok=True)
    for i, f in enumerate(findings, 1):
        f["id"] = f"F-{i:02d}"
        f["image"], f["crop"] = _annotate(f, fig_dir)
        f["guidance"] = repair_guidance(profile, f["judgment"]["category"])
        f["_profile"] = profile

    brief = [{
        "id": f["id"], "label": f["obs"]["label"], "component": f["obs"]["component"],
        "category": f["judgment"]["category"], "severity": f["judgment"]["severity"],
        "priority": f["judgment"]["priority"], "hazard_probability": f["judgment"]["hazard"],
        "action": f["judgment"]["action"], "extent": f["obs"]["extent"],
        "time_s": f["frame"].timestamp_s, "seen_in_frames": len(f["frames"]),
        "also_seen_as": sorted(set(f["labels"]) - {f["obs"]["label"]}),
    } for f in findings]

    job.stage("report", 0.0)
    job.log("Writing executive summary...")
    summary = inspector.executive_summary(job.site, profile, brief) if findings else None

    report_data = {
        "site": job.site, "date": date.today().isoformat(), "source": job.source.name,
        "profile": profile, "profile_name": PROFILES[profile]["name"], "meta": meta,
        "frames_total": len(frames), "frames_failed": frame_errors,
        "observations_raw": len(raw), "dropped_false_alarms": dropped,
        "findings": findings, "summary": summary, "mock": job.mock or job.mock_vision,
        "models": {"vision": getattr(inspector, "model", "mock"),
                   "judgment": next((f["judgment"]["judged_by"] for f in findings), "n/a")},
        "thresholds": THRESHOLDS, "jev_tokens": triage.tokens,
        "credits": getattr(inspector, "credits", []),
        "elapsed_s": round(time.time() - t0, 1),
    }

    (job.out_dir / "findings.json").write_text(json.dumps(
        {**brief_meta(report_data), "summary": summary.model_dump() if summary else None,
         "profile_name": report_data["profile_name"], "elapsed_s": report_data["elapsed_s"],
         "frames_failed": frame_errors, "mock": report_data["mock"],
         "findings": [_jsonable(f) for f in findings]}, indent=2))

    from .report import build_pdf
    pdf = job.out_dir / f"inspection_report_{_slug(job.site)}.pdf"
    build_pdf(report_data, pdf)
    job.stage("done", 1.0)
    job.log("Report ready.")
    return pdf


def _unscored(e: Exception) -> dict:
    return {"category": "other", "category_confidence": 0.0, "severity": 2.0, "severity_probabilities": {},
            "action": "repair", "action_confidence": 0.0, "genuine": 1.0, "hazard": 0.0,
            "priority": "P2", "needs_review": True, "judged_by": f"unscored ({type(e).__name__})"}


def _centre(b):
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


def _merge_duplicates(items: list[dict], same_defect=None, log=print) -> list[dict]:
    """A drone sees the same defect in several frames, sometimes again on a later
    pass. Candidates are sightings with the same label anywhere in the flight, or
    the same category in neighbouring frames (any photo in a set of stills); Jev
    decides whether they are one defect. Without Jev, only neighbouring frames are
    merged, by box distance."""
    items = sorted(items, key=lambda x: x["frame"].index)
    groups: list[dict] = []
    for it in items:
        cat, label = it["judgment"]["category"], it["obs"]["label"]
        match = None
        for g in reversed(groups):
            last = g["_last"]
            gap = it["frame"].index - last["frame"].index
            near_in_time = gap <= 2 or it["frame"].timestamp_s is None
            related = ((label in g["labels"] and same_defect is not None)
                       or (last["judgment"]["category"] == cat and near_in_time))
            if gap <= 0 or not related:
                continue
            if _is_same(last, it, same_defect, log):
                match = g
                break
        if match:
            match["frames"].append(it["frame"])
            match["labels"].append(it["obs"]["label"])
            match["_last"] = it
            if _evidence_score(it) > _evidence_score(match):  # show the worst, clearest sighting
                match.update({k: it[k] for k in ("frame", "analysis", "obs", "judgment")})
        else:
            groups.append({**it, "frames": [it["frame"]], "labels": [it["obs"]["label"]], "_last": it})
    for g in groups:
        g.pop("_last")
    return groups


def _evidence_score(it: dict) -> float:
    vis = {"clear": 1.0, "partial": 0.6, "uncertain": 0.3}.get(it["obs"].get("visibility"), 0.5)
    quality = 1.0 if it["analysis"].image_quality == "good" else 0.6
    x0, y0, x1, y1 = it["obs"]["bbox"]
    closeness = min(1.0, abs(x1 - x0) * abs(y1 - y0) * 3)  # bigger box = closer view
    # Compare severity by whole level only, so clarity decides between sightings of similar severity.
    return round(it["judgment"]["severity"]) * 10 + it["judgment"]["genuine"] + vis + quality + closeness


def _is_same(a: dict, b: dict, same_defect, log) -> bool:
    near = math.dist(_centre(a["obs"]["bbox"]), _centre(b["obs"]["bbox"])) < 0.35
    if same_defect is None:
        return near
    ta, tb = a["frame"].timestamp_s, b["frame"].timestamp_s
    gap = round(tb - ta, 1) if ta is not None and tb is not None else None
    try:
        return same_defect({"obs": a["obs"], "seconds_apart": gap}, {"obs": b["obs"]})
    except Exception as e:
        log(f"  Jev duplicate check failed ({type(e).__name__}); using position instead")
        return near


def _font(size):
    for name in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _annotate(f: dict, out: Path) -> tuple[Path, Path]:
    img = Image.open(f["frame"].path).convert("RGB")
    w, h = img.size
    x0, y0, x1, y1 = [max(0.0, min(1.0, v)) for v in f["obs"]["bbox"]]
    box = (int(min(x0, x1) * w), int(min(y0, y1) * h), int(max(x0, x1) * w), int(max(y0, y1) * h))
    color = PRIORITY_COLORS[f["judgment"]["priority"]]

    # Zoomed crop around the box, padded so the context stays visible.
    pad_x, pad_y = max(40, (box[2] - box[0]) // 2), max(40, (box[3] - box[1]) // 2)
    crop = img.crop((max(0, box[0] - pad_x), max(0, box[1] - pad_y), min(w, box[2] + pad_x), min(h, box[3] + pad_y)))
    crop_path = out / f"{f['id']}_crop.jpg"
    crop.save(crop_path, quality=90)

    draw = ImageDraw.Draw(img)
    stroke = max(3, w // 300)
    draw.rectangle(box, outline=color, width=stroke)
    font = _font(max(16, w // 45))
    tag = f" {f['id']} {f['judgment']['priority']} "
    tb = draw.textbbox((0, 0), tag, font=font)
    ty = box[1] - (tb[3] - tb[1]) - 10 if box[1] > 40 else box[3] + 4
    draw.rectangle((box[0], ty, box[0] + tb[2] + 6, ty + tb[3] + 8), fill=color)
    draw.text((box[0] + 3, ty + 2), tag, fill="white", font=font)
    path = out / f"{f['id']}.jpg"
    img.save(path, quality=90)
    return path, crop_path


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s.lower()).strip("_")[:40] or "site"


def brief_meta(d: dict) -> dict:
    return {k: d[k] for k in ("site", "date", "source", "profile", "meta", "frames_total",
                              "observations_raw", "dropped_false_alarms", "models", "thresholds")}


def _jsonable(f: dict) -> dict:
    return {"id": f["id"], "timestamp_s": f["frame"].timestamp_s, "frames": [x.index for x in f["frames"]],
            "observation": f["obs"], "judgment": f["judgment"], "image": f["image"].name,
            "severity_name": SEVERITY_NAMES[min(4, round(f["judgment"]["severity"]))],
            "crop": f["crop"].name, "guidance": f["guidance"],
            "action_label": action_label(f["_profile"], f["judgment"]["action"])}
