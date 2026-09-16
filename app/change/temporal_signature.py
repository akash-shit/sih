from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import median

from app.change.detector import analyze_tile_pair, analyze_tile_timeline
from app.geospatial import catalog_db as db
from app.config import (
    VELOCITY_ACCEL_RATIO,
    VELOCITY_ACCEL_SLOPE_THRESHOLD,
    VELOCITY_STABLE_THRESHOLD,
)
from app.index.vector_index import VectorIndex


def _effective_score(candidate) -> tuple[float, str]:
    """Return score and source for a candidate while keeping the detector's own
    score as the source of truth for optical-only and SAR-only rescue cases.
    """
    if getattr(candidate, "sar_only", False):
        return candidate.combined_score, "sar_only"
    if getattr(candidate, "fused_score", None) is not None:
        return candidate.fused_score, "fused"
    return candidate.combined_score, "combined"


@dataclass
class VelocityResult:
    tile_id: str
    velocities: list[float]
    score_sources: list[str]
    acceleration: float | None
    trend: str
    latest_velocity: float | None
    series: list[dict]


def _pair_days(candidate) -> int:
    """Compute actual time span between the two observations.

    The project intentionally avoids assuming fixed revisit spacing. For a
    monthly period observation, the effective score is still taken from the
    candidate itself but the interval is measured from the actual date bounds we
    have stored, or a minimum of one day if dates are missing.
    """
    before = getattr(candidate, "date_before", None)
    after = getattr(candidate, "date_after", None)
    if not before or not after:
        return 1
    try:
        dt_before = datetime.fromisoformat(before)
        dt_after = datetime.fromisoformat(after)
        if dt_after >= dt_before:
            return max((dt_after - dt_before).days, 1)
    except ValueError:
        pass
    return 1


def _mean_effective_score_for_pairs(pairs: list) -> float | None:
    if not pairs:
        return None
    values = []
    for candidate in pairs:
        score, _ = _effective_score(candidate)
        values.append(score)
    return sum(values) / len(values)


def compute_velocity(tile_id: str) -> VelocityResult:
    """Compute a per-tile velocity series from the effective score at each pair."""
    candidates = analyze_tile_timeline(tile_id, threshold=0.0)
    if not candidates:
        return VelocityResult(
            tile_id=tile_id,
            velocities=[],
            score_sources=[],
            acceleration=None,
            trend="stable",
            latest_velocity=None,
            series=[],
        )

    velocities = []
    score_sources = []
    series = []
    for candidate in candidates:
        score, source = _effective_score(candidate)
        days = _pair_days(candidate)
        velocity = score / max(days, 1)
        velocities.append(velocity)
        score_sources.append(source)
        series.append({
            "date_pair": {"before": candidate.date_before, "after": candidate.date_after},
            "velocity": velocity,
            "source": source,
        })

    latest_velocity = velocities[-1] if velocities else None
    if len(velocities) >= 3:
        xs = list(range(len(velocities)))
        mean_x = sum(xs) / len(xs)
        mean_y = sum(velocities) / len(velocities)
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, velocities))
        denominator = sum((x - mean_x) ** 2 for x in xs)
        acceleration = (numerator / denominator) if denominator else 0.0
    else:
        acceleration = None

    if all(abs(v) <= VELOCITY_STABLE_THRESHOLD for v in velocities):
        trend = "stable"
    elif acceleration is not None and acceleration > VELOCITY_ACCEL_SLOPE_THRESHOLD and latest_velocity is not None and latest_velocity > VELOCITY_ACCEL_RATIO * median(velocities):
        trend = "accelerating"
    elif acceleration is not None and acceleration < -VELOCITY_ACCEL_SLOPE_THRESHOLD:
        trend = "decelerating"
    else:
        trend = "steady_change"

    return VelocityResult(
        tile_id=tile_id,
        velocities=velocities,
        score_sources=score_sources,
        acceleration=acceleration,
        trend=trend,
        latest_velocity=latest_velocity,
        series=series,
    )


def temporal_profile(tile_id: str) -> dict:
    """Return a short/seasonal/long profile built from the same effective-score logic.

    short is the latest pair score, seasonal is the average of same-month pairs,
    and long is the best available chronology-based comparison if a direct
    first-to-last comparison is unavailable.
    """
    candidates = analyze_tile_timeline(tile_id, threshold=0.0)
    if not candidates:
        return {"short": None, "seasonal": None, "long": None, "score_sources": {}}

    short_candidate = candidates[-1]
    short_score, short_source = _effective_score(short_candidate)
    short = short_score

    seasonal_candidates = []
    if short_candidate.date_before and short_candidate.date_after:
        try:
            last_before = datetime.fromisoformat(short_candidate.date_before)
            last_after = datetime.fromisoformat(short_candidate.date_after)
        except ValueError:
            last_before = last_after = None
        for candidate in candidates:
            try:
                d1 = datetime.fromisoformat(candidate.date_before)
                d2 = datetime.fromisoformat(candidate.date_after)
            except ValueError:
                continue
            if last_before is None or last_after is None:
                continue
            if d1.month == last_before.month and d2.month == last_after.month:
                seasonal_candidates.append(candidate)
    seasonal = _mean_effective_score_for_pairs(seasonal_candidates)
    seasonal_source = "combined" if seasonal is not None else None
    if seasonal is not None:
        _, seasonal_source = _effective_score(seasonal_candidates[-1])

    long_score = None
    long_source = None
    history = db.get_tile_history(tile_id)
    if len(history) >= 2:
        first_row, last_row = history[0], history[-1]
        index = VectorIndex()
        if index.has_vector(first_row["vector_id"]) and index.has_vector(last_row["vector_id"]):
            # TODO(phase2): pass matching SAR observations for the first/last rows via sar_pair.
            long_candidate = analyze_tile_pair(first_row, last_row)
            long_score, long_source = _effective_score(long_candidate)

    if long_score is None:
        long_score = short_score
        long_source = f"{short_source}_fallback_no_direct_comparison"

    return {
        "short": short,
        "seasonal": seasonal,
        "long": long_score,
        "score_sources": {
            "short": short_source,
            "seasonal": seasonal_source,
            "long": long_source,
        },
    }


def velocity_for_all_tiles() -> dict[str, VelocityResult]:
    tiles = db.get_all_tile_ids()
    return {tile_id: compute_velocity(tile_id) for tile_id in tiles}
