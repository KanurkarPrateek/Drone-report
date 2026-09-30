# Getting started

This guide takes you from nothing to your first real report.

## 1. Install the tools

You need three things on your computer:

| Tool | What it's for | Install on macOS |
|---|---|---|
| Python 3.12 | runs the app | installed by uv below |
| uv | installs Python and the app's libraries | `brew install uv` |
| ffmpeg | cuts videos into frames | `brew install ffmpeg` |

On Linux, install uv with `curl -LsSf https://astral.sh/uv/install.sh | sh` and ffmpeg with your package manager (`sudo apt install ffmpeg`).

Check they work:

```bash
uv --version
ffmpeg -version | head -1
```

## 2. Install the app

```bash
cd video-report
uv venv -p 3.12 .venv
uv pip install -p .venv -r requirements.txt
```

This creates a private Python environment in `.venv/` so nothing is installed system-wide.

> Use Python 3.12. Python 3.14 from Homebrew can fail to create the environment.

## 3. Try it with no keys (Demo mode)

```bash
.venv/bin/python app.py
```

Open **http://localhost:8000**, click **Demo**, drag in any video or photos, type a site name, and click **Generate report**. After a few seconds you can download a PDF.

Demo mode uses your real frames but made-up findings. Every page is stamped DEMO DATA. It's for checking the install works and seeing what a report looks like.

Press `Ctrl+C` in the terminal to stop the server.

## 4. Get API keys

Real reports need two keys:

**Anthropic (Claude)**. Claude looks at each frame and describes the defects it sees.
1. Sign in at [console.anthropic.com](https://console.anthropic.com).
2. Add billing, then create a key under **API keys**. It starts with `sk-ant-`.

**TypeSafe (Jev)**. Jev judges each defect: its type, severity, first action, whether it's real, and whether it's dangerous.
1. Request access at [typesafe.ai](https://typesafe.ai). It's in early access.
2. Create a key. It starts with `apikey_` or `sk-`.

Treat both keys like passwords. Don't paste them into chat tools, tickets or code.

## 5. Your first real report

### In the web app (easiest)

1. Run `.venv/bin/python app.py` and open http://localhost:8000.
2. Paste both keys into **API keys** and click **Test keys**. You should see "✓ Key works" twice.
3. Leave the mode on **Full**.
4. Drop in your footage, fill in the site name and site type, and click **Generate report**.
5. Watch the progress bar: Frames → Detect → Judge → Report. A 30-frame video takes about 1–3 minutes.
6. Read the findings in the page, or click **Download PDF**.

Tick **Remember on this device** to keep the keys in your browser so you don't retype them. They are never saved on the server.

### From the command line

Put your keys in a `.env` file once:

```bash
cp .env.example .env
open -e .env        # paste your two keys, save
```

Then load them into the terminal and run:

```bash
set -a; source .env; set +a
.venv/bin/python -m droneinspect my_flight.mp4 --site "Pad 14" --type oil_gas
```

The PDF path is printed at the end. Everything goes into `out/my_flight/`.

`.env` is listed in `.gitignore`, so your keys won't be committed.

### Only have a Jev key?

Choose **Jev only** in the web app, or run:

```bash
.venv/bin/python -m droneinspect my_flight.mp4 --type solar --mock-vision
```

This uses sample defects in place of Claude, but Jev's scoring is real. It's useful for testing Jev and tuning the priority rules. Reports made this way are stamped DEMO DATA.

## 6. Rebuild the sample reports

```bash
set -a; source .env; set +a      # needs TYPESAFE_API_KEY only
scripts/make_sample_reports.sh
```

This regenerates the eight reports in `out/` from the footage in `samples/`. The defects in those samples were written down ahead of time, so only Jev is called. Some sample videos aren't in git because of their size; see `samples/SOURCES.md` for where to download them.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ffmpeg is required` | Install ffmpeg: `brew install ffmpeg` |
| `ensurepip ... returned non-zero exit status` | Use Python 3.12: `uv venv -p 3.12 .venv` |
| `Missing ANTHROPIC_API_KEY, TYPESAFE_API_KEY` | Load your keys: `set -a; source .env; set +a`, or use `--mock` |
| "Key rejected by Anthropic" | Check the key and that the account has billing enabled |
| "Key works, but this model isn't available to it" | Pick another vision model in the web app, e.g. Claude Opus 5 |
| "Key rejected by TypeSafe" | Check the key; Jev access is invite-only |
| Port 8000 already in use | `PORT=8010 .venv/bin/python app.py` |
| Report has few or no findings | Fly lower or use more frames; see [footage tips](USER_GUIDE.md#getting-good-footage) |
| A frame says "model refused" | Claude declined that frame. The rest of the report still runs, and the frame is listed at the end of the report |
| `Error parsing Opus packet header` in the log | Harmless: the video's audio track is damaged; the frames are fine |
