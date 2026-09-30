#!/usr/bin/env bash
# Rebuild the sample reports in out/ from the footage in samples/.
# The defects for each sample are in samples/*_observations.json, so only Jev is
# called: you need TYPESAFE_API_KEY (e.g. `set -a; source .env; set +a`).
# Footage missing from samples/ is skipped; see samples/SOURCES.md to download it.
set -euo pipefail
cd "$(dirname "$0")/.."

: "${TYPESAFE_API_KEY:?Set TYPESAFE_API_KEY first (set -a; source .env; set +a)}"

PY=.venv/bin/python
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
mkdir -p out

# source | observations | site type | frame option | site name | output name
while IFS='|' read -r src obs type frames site name; do
  if [ ! -e "samples/$src" ]; then
    echo "skip  $name (samples/$src not found)"
    continue
  fi
  echo "build $name"
  # shellcheck disable=SC2086  # $frames is two words on purpose
  $PY -m droneinspect "samples/$src" --site "$site" --type "$type" $frames \
      --observations "samples/$obs" --out "$WORK" </dev/null >/dev/null  # stdin closed: ffmpeg would eat the list
  cp "$WORK/${src%.*}"/*.pdf "out/$name.pdf"
done <<'LIST'
construction_medone_youtube.mp4|construction_site_observations.json|civil|--every 3|Commercial Building Construction - Steel Frame & Excavation|construction_site_report
civil_oroville_spillway.webm|civil_oroville_observations.json|civil|--every 8|Oroville Dam, CA - Spillway Emergency (Feb 2017)|civil_oroville_dam_report
civil_key_bridge_collapse.webm|civil_key_bridge_observations.json|civil|--every 25|Francis Scott Key Bridge, Baltimore - Collapse (Mar 2024)|civil_key_bridge_report
civic_hurricane_irma_stjohn.webm|civic_hurricane_observations.json|building|--every 3|St. John, USVI - Post-Hurricane Irma Community Survey|civic_hurricane_stjohn_report
rural_farm_set|rural_farm_observations.json|building|--max-frames 30|Abandoned Farmstead - Barn, Silos & Sheds|rural_farmstead_report
oil_tank_farm_closeup.mp4|oil_tank_farm_observations.json|oil_gas|--every 2|Tank Farm - Storage Tank & Pipe Rack|oil_tank_farm_report
mosier_oil_train.ogv|mosier_observations.json|oil_gas|--max-frames 16|Mosier, OR - Oil Train Derailment|mosier_oil_train_report
solar_demo_set|solar_observations.json|solar|--max-frames 30|Solar Sample Portfolio (3 sites)|solar_portfolio_report
LIST
echo "done: reports are in out/"
