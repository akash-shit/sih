from app.change.storyline import classify_stage
from app.config import (
    STORYLINE_ACTIVE_THRESHOLD,
    STORYLINE_MAJOR_THRESHOLD,
    STORYLINE_ONSET_THRESHOLD,
    STORYLINE_STABILIZING_THRESHOLD,
)


def test_stabilizing_stage_is_reachable():
    assert classify_stage([0.04], {"short": 0.01, "seasonal": 0.01, "long": 0.01 + STORYLINE_STABILIZING_THRESHOLD + 0.01}) == "stabilizing"


def test_other_storyline_stages():
    assert classify_stage([STORYLINE_ONSET_THRESHOLD], {}) == "stable"
    assert classify_stage([STORYLINE_ONSET_THRESHOLD + 0.01], {"short": 0.0, "seasonal": 0.2}) == "onset"
    assert classify_stage([STORYLINE_ACTIVE_THRESHOLD], {}) == "active_development"
    assert classify_stage([STORYLINE_MAJOR_THRESHOLD], {}) == "major_transformation"
    assert classify_stage([], {}) == "monitoring"