"""Offline stand-ins for Claude and Jev so the pipeline and PDF can be tested without API keys.

The findings are made up. A report built in mock mode is stamped "DEMO DATA".
"""

import random

from .profiles import PROFILES, SEVERITY_LEVELS
from .triage import priority_for
from .vision import AssetGuess, ExecSummary, FrameAnalysis, Observation

SAMPLES = {
    "oil_gas": [
        ("Dark stain spreading from flange", "flange on 6\" flowline", "hydrocarbon_leak", 3.4, 0.8, "repair",
         "Wet-looking black stain on soil directly under a bolted flange, darker at the centre.", "~1.5 m diameter",
         "Isolate the line, replace the flange gasket and remove contaminated soil."),
        ("Rust on pipe elbow", "above-ground pipe elbow", "corrosion", 2.1, 0.1, "repair",
         "Orange-brown scaling over the elbow's outer radius, coating gone.", "~40 cm band",
         "UT-gauge the elbow wall; blast and recoat if above minimum thickness."),
        ("Peeling coating on tank shell", "storage tank shell", "coating_failure", 1.2, 0.05, "repair",
         "Paint flaking in patches on the lower tank course.", "~3 m2",
         "Spot-blast and recoat the lower course per the coating spec."),
        ("Eroded containment berm", "secondary containment berm", "containment_breach", 2.6, 0.55, "repair",
         "Gap in the earthen berm on the north side with a visible wash channel.", "~2 m gap",
         "Rebuild the berm section with compacted fill and check containment capacity."),
    ],
    "solar": [
        ("Shattered module glass", "PV module, row 4", "physical_damage", 3.2, 0.7, "replace",
         "Spider-web crack pattern across the full module surface.", "1 module",
         "Isolate the string and replace the module."),
        ("Heavy bird soiling", "PV modules, row 2", "soiling", 1.1, 0.02, "clean",
         "White droppings concentrated on the top edge of several modules.", "5 modules",
         "Clean with deionised water; add bird deterrents on the top rail."),
        ("Vegetation shading lower row", "array edge, row 7", "shading", 1.4, 0.05, "clean",
         "Tall grass and shrubs casting shadows on the bottom cells.", "~12 modules",
         "Cut back vegetation along the row and schedule recurring mowing."),
        ("Hanging DC cable", "string cable under row 3", "cable_issue", 2.3, 0.45, "repair",
         "Cable loop hanging to ground level, unsupported between clips.", "~2 m run",
         "Isolate and re-secure the cable with UV-rated clips; inspect for abrasion."),
    ],
}
SAMPLES["generic"] = SAMPLES["oil_gas"]


class MockInspector:
    def __init__(self, profile_key: str = "oil_gas"):
        self.profile_key = profile_key

    def guess_asset(self, frames):
        return AssetGuess(asset_type=self.profile_key, site_description="Demo site")

    def analyse(self, frame, profile_key, timestamp_s):
        rng = random.Random(frame.name)
        obs = []
        if rng.random() < 0.6:
            s = rng.choice(SAMPLES[profile_key])
            x, y = rng.uniform(0.1, 0.6), rng.uniform(0.1, 0.6)
            obs.append(Observation(
                label=s[0], component=s[1], description=s[6], visual_evidence=s[6], extent=s[7],
                bbox=[x, y, x + rng.uniform(0.15, 0.3), y + rng.uniform(0.15, 0.3)],
                suggested_fix=s[8], visibility="clear"))
        return FrameAnalysis(scene="Demo frame", image_quality="good", is_thermal=False, observations=obs)

    def executive_summary(self, site, profile_key, findings):
        p1 = [f["id"] for f in findings if f["priority"] == "P1"]
        return ExecSummary(
            overall_condition="Poor" if p1 else "Fair",
            summary=(f"DEMO DATA. The drone survey of {site} found {len(findings)} defects, "
                     f"{len(p1)} of which need immediate action ({', '.join(p1) or 'none'})."),
            key_risks=[f"{f['id']}: {f['label']}" for f in findings[:3]],
            immediate_actions=[f"Act on {i}" for i in p1] or ["None"],
            next_30_days=["Complete all P2 repairs."],
            next_90_days=["Re-fly the site to confirm repairs and track P3 items."],
        )


class MockTriage:
    def __init__(self, profile_key: str):
        self.profile_key = profile_key
        self.tokens = 0

    def judge(self, observation, context):
        s = next((s for s in SAMPLES[self.profile_key] if s[0] == observation["label"]), SAMPLES[self.profile_key][0])
        sev, hazard = s[3], s[4]
        lo = int(sev)
        probs = {i: 0.0 for i in range(len(SEVERITY_LEVELS))}
        probs[lo] = round(1 - (sev - lo), 3)
        if lo + 1 < len(SEVERITY_LEVELS):
            probs[lo + 1] = round(sev - lo, 3)
        return {
            "category": s[2] if s[2] in PROFILES[self.profile_key]["categories"] else "other",
            "category_confidence": 0.9, "severity": sev, "severity_probabilities": probs,
            "action": s[5], "action_confidence": 0.85, "genuine": 0.9, "hazard": hazard,
            "priority": priority_for(sev, hazard), "needs_review": False, "judged_by": "mock",
        }
