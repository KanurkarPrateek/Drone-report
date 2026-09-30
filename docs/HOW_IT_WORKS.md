# How it works

- [The pipeline](#the-pipeline)
- [Why two models](#why-two-models)
- [The priority rules](#the-priority-rules)
- [Merging repeat sightings](#merging-repeat-sightings)
- [Code map](#code-map)
- [Adding a site type](#adding-a-site-type)
- [Web API](#web-api)
- [Configuration](#configuration)
- [Deploying](#deploying)
- [Limits](#limits)

## The pipeline

```
 footage
    │
    ▼
 1. Frames      ffmpeg takes evenly spaced stills (frames.py)
    │
    ▼
 2. Detect      Claude looks at each frame and lists every visible defect:
    │           what it is, where (a box), how big, the evidence, a suggested fix
    │           (vision.py, 4 frames at a time)
    ▼
 3. Judge       Jev scores each defect: category, severity 0-4, first action,
    │           chance it's real, chance it's a hazard (triage.py, 8 at a time)
    ▼
 4. Decide      Plain code applies the rules: drop false alarms, merge repeats,
    │           set P1/P2/P3, mark "verify on site" (pipeline.py, triage.py)
    ▼
 5. Summarise   Claude writes the executive summary and action plan from the
    │           ranked findings (vision.py)
    ▼
 6. Report      PDF with annotated photos and repair playbooks (report.py),
                plus findings.json
```

One frame that fails (a network error, a refusal) doesn't stop the report; it's listed at the end of the PDF. If Claude declines a frame, the request falls back to another Claude model on the server side (`fallbacks="default"`).

## Why two models

**Claude** is a vision-language model: it can look at an image and describe what's wrong in words. That's the "seeing" step.

**Jev** (TypeSafe AI's "System One" model) can't see images or write text. It reads JSON and returns *typed answers with probabilities*: one label from a fixed list, a score on a fixed scale, or a yes/no probability. That suits the "judging" step:

- **Consistent labels.** Every finding lands in the site type's fixed category list, so reports can be compared flight to flight.
- **Probabilities, not just answers.** Severity comes with a spread across the five levels, which the report draws as a small chart.
- **Tunable false-alarm filter.** "Is this a real defect or a shadow?" is a probability, so the cut-off is a number you can change.
- **Explainable priority.** Code turns Jev's numbers into P1/P2/P3 with rules anyone can read (below). No hidden prompt decides urgency.
- **Cheap and fast.** About $0.04 per million input tokens and under a second per call, so every observation gets judged.

The five questions Jev answers for each defect are in `build_questions()` in `droneinspect/triage.py`. Jev also answers a sixth question when merging: "are these two sightings the same defect?"

## The priority rules

All in `THRESHOLDS` at the top of `droneinspect/triage.py`:

| Rule | Value | Effect |
|---|---|---|
| `drop_if_genuine_below` | 0.35 | Below this chance of being real, the finding is left out |
| `review_if_genuine_below` | 0.60 | Below this, it's kept but marked **Verify on site** and capped at P2 |
| `review_if_category_conf_below` | 0.50 | Unsure category also marks **Verify on site** |
| `hazard_forces_p1` | 0.60 | Hazard chance at or above this makes it **P1** |
| `p1_min_severity` | 3.5 | Severity at or above this makes it **P1** |
| `shutdown_forces_p1` + `shutdown_min_severity` | 0.50 + 2.5 | If Jev leans "shut down / keep out" and severity is at least 2.5, **P1** |
| `p2_min_severity` | 1.75 | Otherwise, severity at or above this is **P2**; below it is **P3** |
| `same_defect_above` | 0.60 | Jev's "same defect" chance needed to merge two sightings |

The methodology page of every report prints the rules that were used, so a report always explains itself.

To pin Jev's version once you've tuned these, set `JEV_MODEL=jev-1.13.0` (or whichever version you tuned against). The version that answered is printed on each report.

## Merging repeat sightings

A drone sees the same defect in several frames. `_merge_duplicates()` in `pipeline.py` groups them:

- **Candidates**: sightings with the same category in neighbouring frames (any two photos in a photo set), or with exactly the same label anywhere in the flight.
- **Decision**: Jev is asked whether each candidate pair is the same physical defect. Without Jev (demo mode), only neighbouring frames with nearby boxes are merged.
- **Which photo is shown**: the worst severity level first, then the clearest view (visibility, image quality, how large the defect appears in the frame).

Jev's scores vary slightly between runs. When a "same defect?" answer lands close to the 0.60 cut-off, running the same footage twice can give one finding or two. Pinning `JEV_MODEL` helps; the thresholds may also need tuning on your own footage.

## Code map

```
video-report/
├── app.py                      web server and JSON API (Flask)
├── web/index.html              the web app (one page, no build step)
├── droneinspect/
│   ├── __main__.py             command line
│   ├── pipeline.py             runs the steps; merging; evidence images
│   ├── frames.py               video/photos → frames (ffmpeg, Pillow)
│   ├── vision.py               Claude: detection, site-type guess, summary
│   ├── triage.py               Jev: questions, priority rules, same-defect check
│   ├── profiles.py             site types: what to look for, categories, repair playbooks
│   ├── report.py               PDF layout (ReportLab)
│   ├── replay.py               load findings from a JSON file instead of Claude
│   └── mock.py                 fake Claude and Jev for demo mode
├── samples/                    sample footage, findings files, SOURCES.md
├── scripts/make_sample_reports.sh
├── docs/                       these guides
└── out/                        reports
```

Libraries: `anthropic` (Claude), `typesafe-sdk` (Jev), `reportlab` (PDF), `pillow` (images), `flask` (web). ffmpeg is called as a command.

## Adding a site type

Everything about a site type lives in one entry in `PROFILES` in `droneinspect/profiles.py`. To add, say, wind turbines:

1. Copy an existing entry and give it a key, e.g. `"wind"`.
2. Set `name` (shown on reports) and `look_for` (tells Claude what to inspect).
3. Set `categories`: each label with a one-line description. Jev picks from these, so keep them distinct. Keep an `other`.
4. Set `playbook`: for each category, the `steps`, `crew` and `references` (standards) printed in the report.
5. Optional: `actions` and `action_labels` to reword the five first actions (the building type says "Keep out / make safe" instead of "Shut down").
6. Add the key to the `asset_type` choices in `vision.py` (`AssetGuess`) and to `--type` in `__main__.py`.

The web app picks the new type up automatically.

## Web API

The web page uses these routes; other tools can too.

| Method and path | Does |
|---|---|
| `GET /api/config` | Lists vision models, site types, and whether server keys are available |
| `POST /api/keys/test` | Checks keys. JSON body: `anthropic_key`, `typesafe_key`, `vision_model` |
| `POST /api/jobs` | Starts a job. Form upload: `files` (one or more), `site`, `profile`, `max_frames`, `mode` (`full`, `jev_only`, `demo`), `vision_model`, `anthropic_key`, `typesafe_key`. Returns `{"id": ...}` |
| `GET /api/jobs/<id>` | Status, stage, progress (0–1) and log; when done, the full findings |
| `GET /api/jobs/<id>/pdf` | Downloads the PDF (`?inline=1` to view in the browser) |
| `GET /api/jobs/<id>/img/<name>` | An evidence image, e.g. `F-01_crop.jpg` |

Example:

```bash
curl -F files=@flight.mp4 -F site="Pad 14" -F profile=oil_gas -F mode=full \
     -F anthropic_key=$ANTHROPIC_API_KEY -F typesafe_key=$TYPESAFE_API_KEY \
     http://localhost:8000/api/jobs
```

## Configuration

| Setting | Where | Default | Purpose |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | environment / `.env` | none | Claude key for the command line |
| `TYPESAFE_API_KEY` | environment / `.env` | none | Jev key for the command line |
| `JEV_MODEL` | environment | `jev-latest` | Pin a Jev version |
| `PORT` | environment | 8000 | Web server port |
| `HOST` | environment | 127.0.0.1 | Web server address; `0.0.0.0` to accept other machines |
| `DRONEINSPECT_SERVER_KEYS` | environment | off | `1` lets web jobs without keys use the server's own keys |
| Vision model | `MODEL` in `vision.py` | `claude-fable-5-1` | Default Claude model |
| Priority rules | `THRESHOLDS` in `triage.py` | see above | When findings become P1/P2/P3 |
| Run retention | `KEEP_RUNS_H` in `app.py` | 24 hours | How long web reports are kept |

## Deploying

The web app is built for one machine and a small team. Before letting others use it:

- **Use HTTPS.** Users paste API keys into the page; without HTTPS they cross the network in plain text. Put it behind a reverse proxy such as Caddy or nginx with a certificate.
- **Add a login.** There is none; anyone who can reach the page can run jobs.
- **Be careful with `DRONEINSPECT_SERVER_KEYS=1`.** Everyone who reaches the page then spends your keys.
- **Run it with a production server**, e.g. `uv pip install -p .venv gunicorn` then `.venv/bin/gunicorn -w 1 --threads 8 -b 0.0.0.0:8000 app:app`. Keep one worker: jobs are tracked in memory.
- **Storage**: uploads are deleted when a job finishes; frames, images and PDFs are kept under `runs/` for 24 hours.

## Limits

- **Only what's visible.** Normal video can't show wall thickness, internal corrosion, electrical faults or gas leaks that leave no mark. Solar hotspots need a thermal camera; methane needs a gas-imaging camera.
- **No GPS.** Findings are located by timestamp and a box on the frame, not map coordinates. Reading the drone's flight log (DJI SRT/EXIF) to geotag findings is the obvious next step.
- **Sampling.** Only the sampled frames are analysed; something visible for half a second between samples can be missed. Use more frames for long or fast flights.
- **AI can be wrong.** Both models can miss defects or misread shadows and stains. Every P1 and P2 finding must be confirmed on site by a qualified inspector before work starts.
- **MVP infrastructure.** Jobs run in the web server's memory, on one machine, with no database or user accounts.
- **Accuracy hasn't been measured.** There is no labelled test set yet. Collecting inspectors' confirm/reject decisions would give one, and would show where to set the thresholds.
