# droneinspect

Turn drone footage into a PDF inspection report. Upload a video or photos of a site, and you get back every visible defect, where it is in the footage, how serious and how urgent it is, and how to fix it.

It works for five kinds of site:

| Site type | `--type` | Examples |
|---|---|---|
| Oil & gas | `oil_gas` | wells, pipelines, tanks, pipe racks, containment |
| Solar | `solar` | solar farms, rooftop arrays |
| Buildings | `building` | civic and public buildings, housing, barns, silos |
| Civil & construction | `civil` | bridges, dams, roads, slopes, active building sites |
| Anything else | `generic` | general industrial assets |

`auto` (the default) lets the app work out the site type from the footage.

## Quick start (5 minutes)

You need macOS or Linux, [uv](https://docs.astral.sh/uv/) and ffmpeg (`brew install uv ffmpeg`).

```bash
cd video-report
uv venv -p 3.12 .venv
uv pip install -p .venv -r requirements.txt

.venv/bin/python app.py
```

Open **http://localhost:8000**, pick **Demo** mode, drop in any video, and click **Generate report**. Demo mode needs no API keys; its findings are made up and every page is stamped DEMO DATA.

For real reports, paste two API keys into the page:

- **Anthropic API key**: Claude looks at each frame and finds the defects. Get one at [console.anthropic.com](https://console.anthropic.com).
- **Jev API key**: Jev, from TypeSafe AI, judges each defect's type, severity and urgency. Get one at [typesafe.ai](https://typesafe.ai).

## Documentation

| Guide | Read it when you want to |
|---|---|
| [Getting started](docs/GETTING_STARTED.md) | install it, set up keys, run your first report, fix setup problems |
| [User guide](docs/USER_GUIDE.md) | use the web app or command line, read a report, get good footage |
| [How it works](docs/HOW_IT_WORKS.md) | understand the pipeline, tune the rules, add a site type, deploy it |

## Sample reports

`out/` has finished reports made from real footage:

| Report | Site |
|---|---|
| `construction_site_report.pdf` | steel-frame building under construction (not in the git repo: the footage is licensed for internal use only; download it and run the script below) |
| `civil_oroville_dam_report.pdf` | Oroville Dam spillway emergency, 2017 |
| `civil_key_bridge_report.pdf` | Francis Scott Key Bridge collapse, 2024 |
| `civic_hurricane_stjohn_report.pdf` | Hurricane Irma damage, St. John, USVI |
| `rural_farmstead_report.pdf` | abandoned farm: barn, silos, sheds |
| `oil_tank_farm_report.pdf` | storage tank and pipe rack |
| `mosier_oil_train_report.pdf` | crude oil train derailment and fire |
| `solar_portfolio_report.pdf` | three solar sites, including a module fire |

`scripts/make_sample_reports.sh` rebuilds them all. Footage sources and licences are listed in `samples/SOURCES.md`.

## Important

This is an MVP. Reports are AI-assisted and every finding must be confirmed on site by a qualified inspector before repair work starts; the report says so on every page. See [limits](docs/HOW_IT_WORKS.md#limits).
