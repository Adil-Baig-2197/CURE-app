"""Conservative, non-diagnostic emergency-warning rules.

These rules are deliberately independent of ML and intentionally incomplete. They
must be reviewed clinically before any production use.
"""

from typing import Any


def evaluate(responses: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if responses.get("severe_breathing_difficulty") is True:
        reasons.append("Severe breathing difficulty reported")
    if responses.get("blue_or_grey_skin") is True:
        reasons.append("Blue, grey, or unusually pale lips or skin reported")
    if responses.get("chest_pressure_or_spreading") is True:
        reasons.append("Potential emergency chest-pain pattern reported")
    if any(responses.get(key) is True for key in ("face_droop", "one_sided_weakness", "speech_difficulty")):
        reasons.append("Potential sudden stroke symptom reported")
    if responses.get("sudden_confusion") is True:
        reasons.append("Sudden confusion reported")
    if responses.get("unresponsive") is True:
        reasons.append("Unresponsiveness reported")
    return reasons
