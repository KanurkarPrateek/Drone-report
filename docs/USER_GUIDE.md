# User guide

- [The web app](#the-web-app)
- [The command line](#the-command-line)
- [Choosing a site type](#choosing-a-site-type)
- [Reading a report](#reading-a-report)
- [Getting good footage](#getting-good-footage)
- [Using footage from YouTube](#using-footage-from-youtube)
- [Loading findings from a file](#loading-findings-from-a-file)
- [Cost and time](#cost-and-time)

## The web app

Start it with `.venv/bin/python app.py` and open **http://localhost:8000**.

### 1. API keys

Paste your Anthropic and Jev keys and click **Test keys**. The two dots in the top bar turn green when a key works and red when it doesn't.

- Keys are sent only with your job, kept in server memory while it runs, and never written to disk or logs.
- **Remember on this device** stores them in your browser only. Untick it to forget them.

### 2. Mode

| Mode | Keys needed | What happens |
|---|---|---|
| **Full** | Anthropic + Jev | Claude finds the defects, Jev judges them. Real reports. |
| **Jev only** | Jev | Sample defects, real Jev judging. For testing Jev. |
| **Demo** | none | Made-up findings. For trying the app. |

In Full mode you also pick the **vision model**:

| Model | Use it for |
|---|---|
| Claude Fable 5.1 (default) | the best detection of small or subtle defects |
| Claude Opus 5 | about half the cost, still very good |
| Claude Sonnet 5 | quick, cheap checks |

### 3. Footage

Drag in one video, or several photos from one site. Videos: MP4, MOV, WEBM, MKV, AVI. Photos: JPG, PNG, WEBP. Up to 2 GB per upload.

### 4. Details

- **Site name**: printed on the report cover.
- **Site type**: see [choosing a site type](#choosing-a-site-type). "Detect automatically" works well when the footage is clearly one kind of site.
- **Frames to analyse**: how many stills are taken from the video, spread evenly across it. 30 suits most flights of 1–5 minutes. More frames find more but cost more and take longer.

The page shows a rough cost estimate under the slider.

### 5. Results

After you click **Generate report**, the progress bar moves through four steps: **Frames → Detect → Judge → Report**. Open **Show log** to see each step.

When it finishes you get:

- the overall condition (Good / Fair / Poor / Critical) and counts of P1, P2 and P3 findings
- the summary and the 24-hour / 30-day / 90-day action plan
- a card for every finding with a zoomed photo, severity chart, suggested fix and standard repair steps
- filters for **P1**, **P2**, **P3** and **Verify on site**
- **Download PDF** and **Open** buttons

Click any photo to see the full frame. **Recent reports** lists your last 10 runs in this browser, and a link like `http://localhost:8000/#job=<id>` reopens a report.

Reports stay on the server for 24 hours, then they're deleted.

## The command line

```bash
set -a; source .env; set +a     # load your keys
.venv/bin/python -m droneinspect SOURCE [options]
```

`SOURCE` is a video file, one photo, or a folder of photos.

| Option | Default | What it does |
|---|---|---|
| `--site "Name"` | Unnamed site | Site name on the report cover |
| `--type` | `auto` | `oil_gas`, `solar`, `building`, `civil`, `generic` or `auto` |
| `--max-frames N` | 30 | Most frames to take from a video |
| `--every SECONDS` | fit to max-frames | Take one frame every N seconds instead |
| `--out DIR` | `out` | Where to write results |
| `--mock` | off | No API calls, made-up findings |
| `--mock-vision` | off | Made-up defects, real Jev judging |
| `--observations FILE` | none | Use defects written in a file instead of Claude; see [below](#loading-findings-from-a-file) |

Examples:

```bash
# Oil field video, one frame every 3 seconds
.venv/bin/python -m droneinspect pad14.mp4 --site "Permian Pad 14" --type oil_gas --every 3

# Folder of rooftop solar photos
.venv/bin/python -m droneinspect rooftop_photos/ --site "School Roof A" --type solar

# Bridge or construction site, 60 frames for a long flight
.venv/bin/python -m droneinspect bridge.mov --site "River Road Bridge" --type civil --max-frames 60

# Try it without keys
.venv/bin/python -m droneinspect barn.mp4 --type building --mock
```

Each run writes to `out/<video name>/`:

| File | What it is |
|---|---|
| `inspection_report_<site>.pdf` | the report |
| `findings.json` | every finding with Jev's scores, for spreadsheets or other systems |
| `findings/F-01.jpg`, `F-01_crop.jpg`, ... | full frame with the defect boxed, and a zoomed crop |
| `frames/` | the frames taken from the video |

## Choosing a site type

The site type decides what the AI looks for, which defect categories exist, and which repair steps and standards appear in the report.

| Type | Looks for | Categories |
|---|---|---|
| `oil_gas` | leaks and stains, rust, coating and insulation damage, dents and broken supports, containment berms, vegetation, flares, fires | leak, corrosion, coating failure, insulation damage, structural damage, containment breach, vegetation, fire or explosion, flare or venting, security, other |
| `solar` | cracked glass, hotspots (thermal footage), dirt, shading, browning and delamination, missing modules, racking, cables, site condition | physical damage, hotspot, soiling, shading, degradation, missing module, racking damage, cable issue, site condition, other |
| `building` | missing or torn roofing, collapsed or leaning structures, rust, broken walls and windows, vines and trees, loose debris, drainage, damaged power poles and tanks, open derelict buildings | roof damage, structural damage, corrosion, walls and windows, overgrowth, debris, drainage, utilities, security, other |
| `civil` | concrete cracks and spalling, rusted steel, collapsed spans, erosion and scour, landslides, potholes, blocked culverts; on construction sites: open edges, uncovered openings, unshored trenches, people near machines, missing barriers | concrete damage, steel corrosion, structural failure, erosion/scour/washout, slope failure, pavement distress, drainage failure, construction safety, housekeeping and environment, public protection, other |
| `generic` | leaks, rust, cracks, burn marks, debris, safety hazards | leak, corrosion, structural damage, fire damage, vegetation or debris, safety hazard, other |

Use `civil` for building construction sites. It includes the construction safety checks (falls, trenches, machines, public protection).

## Reading a report

Every PDF has the same parts:

1. **Cover**: overall condition, number of findings by priority, footage details, which models were used.
2. **Executive summary**: what was found, the key risks, and a chart of findings by category.
3. **Action plan**: what to do in the next 24–72 hours, 30 days and 90 days.
4. **Findings register**: one line per finding, most urgent first.
5. **Detailed findings**: one page per finding (photos, facts, what was seen, how to fix it, standard procedure, references).
6. **Methodology and limitations**: how the report was made, the rules used, image credits, and any frames that couldn't be analysed.

### Priority

| Priority | Meaning |
|---|---|
| **P1** | Act within 24–72 hours. Danger to people or the environment, or a critical defect. |
| **P2** | Plan the fix within 30 days. |
| **P3** | Fix at the next scheduled maintenance, or monitor. |

### Severity

Jev scores every defect from 0 to 4:

| Score | Level | Meaning |
|---|---|---|
| 0 | Cosmetic | no effect, record only |
| 1 | Minor | early wear; fix at next maintenance |
| 2 | Moderate | measurable damage or lost output; fix in 30–90 days |
| 3 | Major | active damage; fix in 7–30 days |
| 4 | Critical | leak, fire, collapse risk or danger to life; act now |

The score can fall between levels (e.g. 3.46). The small bar chart on each finding page shows how likely Jev thinks each level is.

### Other fields

- **Safety / environmental hazard**: Jev's estimate of the chance the defect is an immediate danger.
- **Likelihood it is a real defect**: Jev's estimate that it isn't a shadow, reflection or normal wear. Below 35% the finding is dropped; below 60% it's kept but marked **Verify on site** and can't be P1.
- **Seen in N frames**: the same defect seen several times is merged into one finding; the report shows the clearest view.
- **Location**: the red box is an approximate location on the frame, not a GPS point.

## Getting good footage

What makes the biggest difference:

- **Fly low and slow.** A crack or a missing bolt needs to be many pixels across. 10–30 m above small assets is typical.
- **Shoot in 4K** if the drone supports it. The app scales frames down, but a sharper source still helps.
- **Get close-ups of anything suspicious** as well as the wide overview.
- **Avoid shooting into the sun.** Glare hides defects, and the report marks those frames as poorly exposed.
- **Keep the camera steady.** Blurry frames are marked and trusted less.
- **Solar hotspots need a thermal camera.** Normal video can't show them.
- **Use photos for spot checks.** A folder of stills works as well as video. Up to `--max-frames` photos are analysed (30 by default), in alphabetical order.

## Using footage from YouTube

The command line can't download web videos by itself. Install the optional downloader once and fetch the file first:

```bash
uv pip install -p .venv yt-dlp
.venv/bin/yt-dlp -f "bv*[height<=2160][ext=mp4]/bv*[height<=2160]" -o "samples/my_site.%(ext)s" "https://youtu.be/VIDEO_ID"
.venv/bin/python -m droneinspect samples/my_site.mp4 --type civil
```

Check the video's licence before you share the report. Most YouTube videos may only be used for internal testing.

## Loading findings from a file

If defects were found another way (by an inspector, another detection model, or a manual review), you can skip Claude and give them to the app in a JSON file. Jev still judges each one and the full report is built as usual.

```bash
.venv/bin/python -m droneinspect footage.mp4 --type civil --every 3 --observations my_findings.json
```

Frames are named `frame_0001.jpg`, `frame_0002.jpg`, ... in the order they're taken, so use the same `--every` or `--max-frames` you used when writing the file. For a folder of photos, frames follow the photos' alphabetical order.

```json
{
  "detected_by": "Site inspector J. Smith",
  "asset_type": "civil",
  "credits": ["Footage: our own drone, 12 June 2026"],
  "frames": {
    "frame_0004.jpg": {
      "scene": "Second-floor deck with workers",
      "image_quality": "good",
      "is_thermal": false,
      "observations": [
        {
          "label": "Open deck edge with no guardrail",
          "component": "second-level deck perimeter",
          "description": "Workers are on the deck and its edges have no guardrails.",
          "visual_evidence": "No stanchions or cables along the edge.",
          "extent": "Whole perimeter, ~60 m",
          "bbox": [0.52, 0.30, 1.0, 0.86],
          "suggested_fix": "Install guardrails before work continues.",
          "visibility": "clear"
        }
      ]
    }
  },
  "summary": { "...": "optional, see below" }
}
```

- `bbox` is `[left, top, right, bottom]` as fractions of the image width and height (0 to 1).
- `image_quality` is one of `good`, `blurry`, `too_far`, `over_or_under_exposed`, `obstructed`.
- `visibility` is `clear`, `partial` or `uncertain`.
- Frames you don't list count as "inspected, nothing found".
- Use the same `label` when the same defect appears in several frames, and they'll be merged.

The optional `summary` block has `overall_condition`, `summary`, `key_risks`, `immediate_actions`, `next_30_days` and `next_90_days`. Finding IDs (F-01, ...) are only known after Jev has ranked them, so refer to findings by words from their label in double braces, e.g. `{{Open deck edge}}`. The app replaces them with the right IDs and stops with an error if a reference matches nothing. Without a summary block, a short one is written automatically.

The files in `samples/*_observations.json` are complete examples.

## Cost and time

Rough figures for a 30-frame video in Full mode:

| | Claude Fable 5.1 | Claude Opus 5 | Claude Sonnet 5 |
|---|---|---|---|
| Claude cost | ~$3–6 | ~$1.50–3 | ~$0.60–1.20 |
| Time | 2–4 min | 1–3 min | 1–2 min |

Jev costs well under one cent per report. These are estimates; check your Anthropic console for real spend.
