from __future__ import annotations

from statistics import median

from app.config import (
    STORYLINE_ACTIVE_THRESHOLD,
    STORYLINE_MAJOR_THRESHOLD,
    STORYLINE_ONSET_THRESHOLD,
    STORYLINE_STABILIZING_THRESHOLD,
)


def classify_stage(velocities, profile) -> str:
    """Interpret a temporal velocity series as a candidate development stage.

    The rules are deliberately simple and evidence-only: they describe what the
    current signal looks like, not a confirmed operational status.
    """
    if not velocities:
        return "monitoring"

    latest = float(velocities[-1])
    median_v = float(median(velocities)) if velocities else 0.0
    short_score = profile.get("short") if isinstance(profile, dict) else None
    seasonal_score = profile.get("seasonal") if isinstance(profile, dict) else None
    long_score = profile.get("long") if isinstance(profile, dict) else None

    if max(abs(v) for v in velocities) <= STORYLINE_ONSET_THRESHOLD:
        return "stable"
    if latest >= STORYLINE_MAJOR_THRESHOLD or (short_score is not None and short_score >= STORYLINE_MAJOR_THRESHOLD):
        return "major_transformation"
    if latest >= STORYLINE_ACTIVE_THRESHOLD or (short_score is not None and short_score >= STORYLINE_ACTIVE_THRESHOLD):
        return "active_development"
    if long_score is not None and short_score is not None and short_score < long_score - STORYLINE_STABILIZING_THRESHOLD:
        return "stabilizing"
    if seasonal_score is not None and short_score is not None and abs(short_score - seasonal_score) > STORYLINE_ONSET_THRESHOLD:
        return "onset"
    return "monitoring"
