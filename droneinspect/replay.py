"""Use observations written ahead of time instead of calling a vision API.

Useful when detection was done elsewhere: by a person, another detector, or
Claude in an interactive session. Jev still judges every observation for real.

File format (JSON):
{
  "detected_by": "who or what produced the observations",
  "asset_type": "oil_gas" | "solar" | "generic",
  "frames": {
    "frame_0004.jpg": {"scene": "...", "image_quality": "good", "is_thermal": false,
                       "observations": [ {Observation fields} ]}
  },
  "credits": ["footage attribution", ...],  # optional
  "summary": { ExecSummary fields }   # optional; cite findings as {{words from the label}}
}
Frames not listed are treated as inspected with nothing found.
"""

import json
import re
from pathlib import Path

from .vision import AssetGuess, ExecSummary, FrameAnalysis


class ReplayInspector:
    def __init__(self, path: Path):
        self.data = json.loads(Path(path).read_text())
        self.model = self.data.get("detected_by", f"observations file ({Path(path).name})")
        self.credits = self.data.get("credits", [])  # image/footage attributions shown in the report

    def guess_asset(self, frames):
        return AssetGuess(asset_type=self.data.get("asset_type", "generic"), site_description="from observations file")

    def analyse(self, frame: Path, profile_key, timestamp_s):
        entry = self.data["frames"].get(frame.name)
        if entry is None:
            return FrameAnalysis(scene="No defects recorded for this frame.", image_quality="good",
                                 is_thermal=False, observations=[])
        return FrameAnalysis.model_validate(entry)

    def executive_summary(self, site, profile_key, findings):
        if self.data.get("summary"):
            # Summaries cite findings as {{words from its label}}; IDs are only known after triage.
            def cite(m):
                words = m.group(1).lower()
                # Match any sighting merged into the finding, not only the one the report shows.
                hits = [f["id"] for f in findings
                        if any(words in label.lower() for label in [f["label"], *f.get("also_seen_as", [])])]
                if not hits:
                    raise ValueError(f"summary cites {{{{{m.group(1)}}}}} but no finding label contains it")
                return ", ".join(dict.fromkeys(hits))
            text = re.sub(r"\{\{(.+?)\}\}", cite, json.dumps(self.data["summary"]))
            # Two citations can resolve to the same finding after merging: "F-02, F-02" -> "F-02".
            text = re.sub(r"\b(F-\d+)((?:, F-\d+)*)", lambda m: ", ".join(dict.fromkeys(m.group(0).split(", "))), text)
            return ExecSummary.model_validate(json.loads(text))
        p1 = [f["id"] for f in findings if f["priority"] == "P1"]
        return ExecSummary(
            overall_condition="Critical" if p1 else "Fair",
            summary=f"The survey of {site} recorded {len(findings)} findings; {len(p1)} need immediate action.",
            key_risks=[f"{f['id']}: {f['label']}" for f in findings[:4]],
            immediate_actions=[f"{f['id']}: {f['label']}" for f in findings if f["priority"] == "P1"] or ["None"],
            next_30_days=[f"{f['id']}: {f['label']}" for f in findings if f["priority"] == "P2"] or ["None"],
            next_90_days=["Re-fly the site to confirm repairs and track remaining items."],
        )
