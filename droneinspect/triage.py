"""The judgment: Jev turns each observation into typed, calibrated decisions.

Jev (TypeSafe's System One model) doesn't read images or write prose. It reads
the JSON observation from the vision step and returns labels and scores with
probabilities. That gives every finding the same taxonomy, a severity with a
probability spread, and a yes/no hazard score. Code, not the model, then turns
those numbers into a priority, using the thresholds below, so a reviewer can
see and tune exactly why something became P1.
"""

import os

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

from .profiles import PROFILES, SEVERITY_LEVELS, actions_for

MODEL = os.environ.get("JEV_MODEL", "jev-latest")

# --- how code reacts to a judgment ------------------------------------------
THRESHOLDS = {
    "drop_if_genuine_below": 0.35,   # likely shadow/reflection/normal wear -> leave out of report
    "hazard_forces_p1": 0.60,        # safety/environmental hazard probability that forces P1
    "p1_min_severity": 3.5,          # expected severity (0-4) at or above which a finding is P1
    "p2_min_severity": 1.75,
    "shutdown_forces_p1": 0.50,      # probability of "isolate_and_shutdown" that forces P1...
    "shutdown_min_severity": 2.5,    # ...but only for defects at least this severe
    "review_if_genuine_below": 0.60, # kept, but flagged "verify on site"
    "review_if_category_conf_below": 0.50,
    "same_defect_above": 0.60,       # Jev says two sightings are the same physical defect
}


def build_questions(profile_key: str) -> dict:
    profile = PROFILES[profile_key]
    return {
        "category": Choice(
            instructions="Which defect category does this observation belong to?",
            criteria=profile["categories"],
        ),
        "severity": Score(
            instructions=(
                f"How severe is this defect for a {profile['name']}? Judge from the description, "
                "visual evidence and extent. Leaks near people, water or ignition sources, and damage "
                "that can grow quickly, are more severe."
            ),
            criteria=SEVERITY_LEVELS,
        ),
        "action": Choice(
            instructions="What is the right first maintenance action for this defect?",
            criteria=actions_for(profile_key),
        ),
        "genuine_defect": Noul(
            instructions=(
                "Is this a real defect, rather than a shadow, reflection, water, normal weathering or a "
                "misreading of the image? Use visibility and image_quality as evidence."
            ),
            criteria={"true": "Real defect a technician would want to know about.",
                      "false": "Likely a false alarm from the image."},
        ),
        "safety_hazard": Noul(
            instructions=(
                "Does this defect pose an immediate risk to people, fire, or the environment "
                "(release to soil/water, electrocution, structural collapse)?"
            ),
        ),
    }


SAME_DEFECT = {
    "same": Noul(
        instructions=(
            "A drone flew over the site and two sightings were reported a few seconds apart. Are they the "
            "same physical defect seen twice (the camera moved), rather than two separate defects? Compare "
            "component, description, extent and position in the frame; positions shift as the drone moves."
        ),
        criteria={"true": "Same defect: merge into one finding.", "false": "Different defects: keep both."},
    ),
}


def priority_for(severity: float, hazard: float, shutdown: float = 0.0, genuine: float = 1.0) -> str:
    # Probably-not-real findings get checked before anyone is dispatched in a hurry.
    if genuine < THRESHOLDS["review_if_genuine_below"]:
        return "P2"
    if (hazard >= THRESHOLDS["hazard_forces_p1"] or severity >= THRESHOLDS["p1_min_severity"]
            or (shutdown >= THRESHOLDS["shutdown_forces_p1"] and severity >= THRESHOLDS["shutdown_min_severity"])):
        return "P1"
    if severity >= THRESHOLDS["p2_min_severity"]:
        return "P2"
    return "P3"


class Triage:
    def __init__(self, profile_key: str, model: str = MODEL, api_key: str | None = None):
        self.client = TypeSafeClient(api_key=api_key)  # None -> TYPESAFE_API_KEY
        self.profile_key = profile_key
        self.questions = build_questions(profile_key)
        self.model = model
        self.tokens = 0

    def judge(self, observation: dict, context: dict) -> dict:
        state = {
            "asset_type": PROFILES[self.profile_key]["name"],
            "frame": context,
            "observation": observation,
        }
        r = self.client.system_one(state=state, questions=self.questions, model=self.model)
        a = r.answers
        self.tokens += (r.usage.input_tokens or 0)
        severity = a["severity"].score
        hazard = a["safety_hazard"].noul
        shutdown = a["action"].probabilities.get("isolate_and_shutdown", 0.0)
        genuine = a["genuine_defect"].noul
        return {
            "category": a["category"].choice,
            "category_confidence": round(a["category"].confidence, 3),
            "severity": round(severity, 2),
            "severity_probabilities": {int(k): round(v, 3) for k, v in a["severity"].probabilities.items()},
            "action": a["action"].choice,
            "action_confidence": round(a["action"].confidence, 3),
            "genuine": round(genuine, 3),
            "hazard": round(hazard, 3),
            "priority": priority_for(severity, hazard, shutdown, genuine),
            "needs_review": (genuine < THRESHOLDS["review_if_genuine_below"]
                             or a["category"].confidence < THRESHOLDS["review_if_category_conf_below"]),
            "judged_by": r.model,
        }

    def same_defect(self, a: dict, b: dict) -> bool:
        """Ask Jev whether two sightings in nearby frames are one defect."""
        state = {"asset_type": PROFILES[self.profile_key]["name"],
                 "seconds_apart": a["seconds_apart"], "first_sighting": a["obs"], "second_sighting": b["obs"]}
        r = self.client.system_one(state=state, questions=SAME_DEFECT, model=self.model)
        self.tokens += (r.usage.input_tokens or 0)
        return r.answers["same"].noul >= THRESHOLDS["same_defect_above"]
