"""The eyes: Claude looks at each frame and describes every visible defect.

Jev can't see images, so this step turns pixels into structured observations.
It deliberately does NOT decide severity or priority; that is Jev's job.
"""

import base64
import json
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel

from .profiles import PROFILES

MODEL = "claude-fable-5-1"   # Anthropic's most capable model; "claude-opus-5" is cheaper
MODELS = {
    "claude-fable-5-1": "Claude Fable 5.1 (most capable)",
    "claude-opus-5": "Claude Opus 5 (about half the cost)",
    "claude-sonnet-5": "Claude Sonnet 5 (fastest, cheapest)",
}
# Route refusals to a substitute model server-side instead of losing the frame.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class Observation(BaseModel):
    label: str                 # short name, e.g. "rust on flange at pipe elbow"
    component: str             # what it is on: "pipe flange", "PV module", "tank shell"
    description: str           # what is visibly wrong, in plain words
    visual_evidence: str       # the exact cues seen: colour, shape, texture, spread
    extent: str                # size/spread estimate, e.g. "~2 m stain", "3 modules"
    bbox: list[float]          # [x0, y0, x1, y1] as fractions of width/height
    suggested_fix: str         # the specific fix for this instance
    visibility: Literal["clear", "partial", "uncertain"]


class FrameAnalysis(BaseModel):
    scene: str                 # one sentence: what the frame shows
    image_quality: Literal["good", "blurry", "too_far", "over_or_under_exposed", "obstructed"]
    is_thermal: bool
    observations: list[Observation]


class AssetGuess(BaseModel):
    asset_type: Literal["oil_gas", "solar", "building", "civil", "generic"]
    site_description: str


class ExecSummary(BaseModel):
    overall_condition: Literal["Good", "Fair", "Poor", "Critical"]
    summary: str               # 1 paragraph, 4-6 sentences
    key_risks: list[str]       # 3-5 bullets, each citing finding IDs
    immediate_actions: list[str]
    next_30_days: list[str]
    next_90_days: list[str]


def _image_block(path: Path) -> dict:
    data = base64.standard_b64encode(path.read_bytes()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}}


class Inspector:
    def __init__(self, model: str = MODEL, api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.model = model

    def _parse(self, content: list, schema: type[BaseModel], system: str, max_tokens: int = 16000):
        resp = self.client.beta.messages.parse(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_format=schema,
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        if resp.stop_reason == "refusal":
            raise RuntimeError(f"model refused: {resp.stop_details}")
        return resp.parsed_output

    def guess_asset(self, frames: list[Path]) -> AssetGuess:
        content = [_image_block(p) for p in frames[:3]]
        content.append({"type": "text", "text": (
            "These are frames from a drone inspection flight. Which kind of site is it? "
            "oil_gas = oil/gas wells, pipelines, tanks, refinery or processing equipment. "
            "solar = photovoltaic panels (ground-mount farm or rooftop). building = houses, civic/public "
            "buildings, farm buildings, roofs or neighbourhoods. civil = bridges, dams, roads, culverts, "
            "slopes or construction sites. generic = anything else."
        )})
        return self._parse(content, AssetGuess, "You classify industrial sites from aerial imagery.", 1024)

    def analyse(self, frame: Path, profile_key: str, timestamp_s: float | None) -> FrameAnalysis:
        profile = PROFILES[profile_key]
        system = (
            f"You are a certified drone inspection analyst reviewing aerial footage of a {profile['name']}. "
            "Your job is to find every visible defect so a maintenance team can act on it. "
            f"Inspect: {profile['look_for']}\n\n"
            "Rules:\n"
            "- Report only what is visible in this frame. Do not guess at hidden damage.\n"
            "- One observation per distinct defect. Group identical defects on adjacent components "
            "(e.g. 'soiling on 6 modules in row 3') instead of listing each one.\n"
            "- bbox is [x0, y0, x1, y1] as fractions (0-1) of image width and height, tight around the defect.\n"
            "- Mark visibility 'uncertain' when it could be a shadow, reflection, water or normal wear.\n"
            "- If nothing is wrong, return an empty observations list. Do not invent defects.\n"
            "- suggested_fix: one or two concrete sentences a field technician could act on."
        )
        when = f"at {timestamp_s:.1f}s into the flight" if timestamp_s is not None else "from a still image"
        content = [_image_block(frame), {"type": "text", "text": f"Frame captured {when}. List every defect you can see."}]
        return self._parse(content, FrameAnalysis, system)

    def executive_summary(self, site: str, profile_key: str, findings: list[dict]) -> ExecSummary:
        content = [{"type": "text", "text": (
            f"Site: {site}\nAsset type: {PROFILES[profile_key]['name']}\n\n"
            "Triaged findings from a drone inspection (severity 0-4, priority P1 most urgent):\n"
            f"{json.dumps(findings, indent=1)}\n\n"
            "Write the executive summary for the asset owner. Be specific, cite finding IDs, and do not "
            "mention findings that are not in the list. Plain business English, no hype."
        )}]
        return self._parse(content, ExecSummary, "You write concise, factual asset inspection reports for operations managers.", 8000)

