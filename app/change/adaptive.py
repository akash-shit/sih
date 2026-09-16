"""Land-cover adaptive scoring, strategic priority and active learning."""
from dataclasses import dataclass
import math
from .landcover import classify_land_cover

LAND_COVER_WEIGHTS = {
    "water": (0.45, 0.55), "dense_vegetation": (0.75, 0.25),
    "sparse_vegetation": (0.60, 0.40), "urban": (0.80, 0.20),
    "bare": (0.65, 0.35), "unknown": (0.65, 0.35),
}

def infer_land_cover(ndvi: float | None, ndwi: float | None) -> str:
    return classify_land_cover(ndvi, ndwi)

def adaptive_score(embedding_drift: float, spectral_delta: float, *, land_cover="unknown") -> float:
    ew, sw = LAND_COVER_WEIGHTS.get(land_cover, LAND_COVER_WEIGHTS["unknown"])
    return float(max(0.0, min(1.0, ew * embedding_drift + sw * min(spectral_delta / 0.5, 1.0))))

@dataclass(frozen=True)
class Priority:
    score: float
    reasons: tuple[str, ...]

def strategic_priority(change_score: float, *, criticality: float = 0.5, population_exposure: float = 0.0,
                       proximity_to_assets: float = 0.0, confidence: float = 0.5) -> Priority:
    values = [max(0.0, min(1.0, x)) for x in (change_score, criticality, population_exposure, proximity_to_assets, confidence)]
    score = 0.45 * values[0] + 0.20 * values[1] + 0.15 * values[2] + 0.10 * values[3] + 0.10 * values[4]
    reasons = tuple(label for label, value in (("high_change", values[0]), ("critical_area", values[1]),
                    ("population_exposure", values[2]), ("near_asset", values[3])) if value >= 0.6)
    return Priority(round(score, 6), reasons)

def active_learning_probability(score: float, *, uncertainty: float | None = None, diversity: float = 0.0) -> float:
    """Probability of confirmation used for reranking; uncertainty boosts review."""
    base = 1 / (1 + math.exp(-8 * (float(score) - 0.5)))
    if uncertainty is not None:
        base = 0.7 * base + 0.3 * float(max(0, min(1, uncertainty)))
    return float(max(0, min(1, 0.85 * base + 0.15 * max(0, min(1, diversity)))))
