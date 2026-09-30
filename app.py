"""Web UI: bring your own API keys, upload footage, get the report.

    .venv/bin/python app.py                       # http://localhost:8000

API keys are sent with each job, held in memory for that job only, and never
written to disk or logs. Set DRONEINSPECT_SERVER_KEYS=1 to let jobs without keys
fall back to ANTHROPIC_API_KEY / TYPESAFE_API_KEY from the server environment
(only do that on a private deployment: anyone who can reach the page spends them).
"""

import json
import os
import shutil
import threading
import time
import uuid
from pathlib import Path

import anthropic
from flask import Flask, abort, jsonify, request, send_file, send_from_directory
from typesafe_sdk import TypeSafeClient
from werkzeug.utils import secure_filename

from droneinspect.pipeline import Job, run
from droneinspect.profiles import PROFILES
from droneinspect.vision import MODEL as DEFAULT_VISION, MODELS as VISION_MODELS

HERE = Path(__file__).parent
ROOT = HERE / "runs"
SERVER_KEYS = os.environ.get("DRONEINSPECT_SERVER_KEYS") == "1"
KEEP_RUNS_H = 24
# Progress bar: where each pipeline stage starts and how wide it is.
STAGES = {"frames": (0.00, 0.05), "see": (0.05, 0.70), "judge": (0.75, 0.15), "report": (0.90, 0.10), "done": (1.0, 0.0)}

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024**3  # 2 GB
jobs: dict[str, dict] = {}


def _key(form_value: str | None, env_name: str) -> str | None:
    v = (form_value or "").strip()
    if v:
        return v
    return os.environ.get(env_name) if SERVER_KEYS else None


def _cleanup_old_runs():
    if not ROOT.exists():
        return
    cutoff = time.time() - KEEP_RUNS_H * 3600
    for d in ROOT.iterdir():
        if d.is_dir() and d.stat().st_mtime < cutoff:
            shutil.rmtree(d, ignore_errors=True)
            jobs.pop(d.name, None)


@app.get("/")
def index():
    return send_from_directory(HERE / "web", "index.html")


@app.get("/api/config")
def config():
    return jsonify(
        vision_models=[{"id": k, "name": v} for k, v in VISION_MODELS.items()],
        default_vision=DEFAULT_VISION,
        profiles=[{"id": "auto", "name": "Detect automatically"}] +
                 [{"id": k, "name": v["name"]} for k, v in PROFILES.items()],
        server_keys={"anthropic": SERVER_KEYS and bool(os.environ.get("ANTHROPIC_API_KEY")),
                     "typesafe": SERVER_KEYS and bool(os.environ.get("TYPESAFE_API_KEY"))},
    )


@app.post("/api/keys/test")
def test_keys():
    body = request.get_json(force=True, silent=True) or {}
    out = {}
    if (k := _key(body.get("anthropic_key"), "ANTHROPIC_API_KEY")):
        try:
            anthropic.Anthropic(api_key=k, max_retries=0, timeout=15).models.retrieve(body.get("vision_model") or DEFAULT_VISION)
            out["anthropic"] = {"ok": True}
        except anthropic.AuthenticationError:
            out["anthropic"] = {"ok": False, "error": "Key rejected by Anthropic."}
        except anthropic.NotFoundError:
            out["anthropic"] = {"ok": False, "error": "Key works, but this model isn't available to it."}
        except anthropic.APIError as e:
            out["anthropic"] = {"ok": False, "error": f"{type(e).__name__}"}
    if (k := _key(body.get("typesafe_key"), "TYPESAFE_API_KEY")):
        try:
            with TypeSafeClient(api_key=k, timeout=15) as c:
                c.models.list()
            out["typesafe"] = {"ok": True}
        except Exception as e:
            out["typesafe"] = {"ok": False, "error": "Key rejected by TypeSafe." if "Auth" in type(e).__name__ else type(e).__name__}
    return jsonify(out)


@app.post("/api/jobs")
def create_job():
    _cleanup_old_runs()
    files = [f for f in request.files.getlist("files") if f.filename]
    if not files:
        return jsonify(error="Choose a video or some photos first."), 400

    form = request.form
    mode = form.get("mode", "full")  # full | jev_only | demo
    anthropic_key = _key(form.get("anthropic_key"), "ANTHROPIC_API_KEY")
    typesafe_key = _key(form.get("typesafe_key"), "TYPESAFE_API_KEY")
    if mode in ("full", "jev_only") and not typesafe_key:
        return jsonify(error="Add your Jev (TypeSafe) API key, or switch to Demo mode."), 400
    if mode == "full" and not anthropic_key:
        return jsonify(error="Add your Anthropic API key, or switch to 'Jev only' mode."), 400
    vision_model = form.get("vision_model") or DEFAULT_VISION
    if vision_model not in VISION_MODELS:
        return jsonify(error="Unknown vision model."), 400
    profile = form.get("profile", "auto")
    if profile != "auto" and profile not in PROFILES:
        return jsonify(error="Unknown site type."), 400

    job_id = uuid.uuid4().hex
    run_dir = ROOT / job_id
    upload = run_dir / "upload"
    upload.mkdir(parents=True)
    for f in files:
        f.save(upload / (secure_filename(f.filename) or f"file_{uuid.uuid4().hex[:6]}"))
    saved = list(upload.iterdir())
    source = saved[0] if len(saved) == 1 else upload  # one video, or a folder of photos

    state = {"status": "running", "stage": "frames", "progress": 0.0, "log": [], "error": None,
             "site": form.get("site") or "Unnamed site", "created": time.time(), "mode": mode,
             "vision_model": vision_model if mode == "full" else "demo", "pdf": None}
    jobs[job_id] = state

    def stage(name, frac):
        start, width = STAGES[name]
        state["stage"], state["progress"] = name, round(start + width * frac, 3)

    job = Job(
        source=source, out_dir=run_dir / "report", site=state["site"], profile=profile,
        max_frames=max(3, min(120, int(form.get("max_frames") or 30))),
        mock=mode == "demo", mock_vision=mode == "jev_only",
        anthropic_key=anthropic_key, typesafe_key=typesafe_key, vision_model=vision_model,
        log=state["log"].append, stage=stage,
    )

    def work():
        try:
            state["pdf"] = run(job)
            state["status"] = "done"
        except Exception as e:
            msg = str(e)
            for k in (anthropic_key, typesafe_key):  # belt and braces: never echo a key
                if k:
                    msg = msg.replace(k, "***")
            state["error"] = f"{type(e).__name__}: {msg}"[:400]
            state["log"].append("Failed: " + state["error"])
            state["status"] = "failed"
        finally:
            shutil.rmtree(upload, ignore_errors=True)  # keep frames + report, drop the raw upload

    threading.Thread(target=work, daemon=True).start()
    return jsonify(id=job_id)


def _job(job_id):
    s = jobs.get(job_id)
    if not s:
        abort(404)
    return s


@app.get("/api/jobs/<job_id>")
def job_status(job_id):
    s = _job(job_id)
    out = {k: s[k] for k in ("status", "stage", "progress", "log", "error", "site", "created", "mode", "vision_model")}
    if s["status"] == "done":
        out["result"] = json.loads((ROOT / job_id / "report" / "findings.json").read_text())
    return jsonify(out)


@app.get("/api/jobs/<job_id>/pdf")
def job_pdf(job_id):
    s = _job(job_id)
    if not s["pdf"]:
        abort(404)
    return send_file(s["pdf"], as_attachment=request.args.get("inline") != "1", download_name=s["pdf"].name)


@app.get("/api/jobs/<job_id>/img/<name>")
def job_image(job_id, name):
    _job(job_id)
    return send_from_directory(ROOT / job_id / "report" / "findings", secure_filename(name))


@app.errorhandler(413)
def too_big(_):
    return jsonify(error="Upload is larger than 2 GB."), 413


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 8000)), threaded=True)
