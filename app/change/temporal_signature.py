from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import median
from time import monotonic

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


_VELOCITY_CACHE: tuple[float, dict[str, VelocityResult]] | None = None
_VELOCITY_CACHE_TTL = 20.0


def _coerce_date(value):
    """Normalize iso-like date strings into datetime objects."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _frame_date(observation) -> str | None:
    if isinstance(observation, dict):
        candidates = [observation.get("date"), observation.get("acquisition_date"), observation.get("date_after"), observation.get("date_before")]
    else:
        candidates = [getattr(observation, "date", None), getattr(observation, "acquisition_date", None), getattr(observation, "date_after", None), getattr(observation, "date_before", None)]
    for candidate in candidates:
        if not candidate:
            continue
        dt = _coerce_date(candidate)
        if dt is not None:
            return dt.date().isoformat()
    return None


def _candidate_dates(candidate):
    before = getattr(candidate, "date_before", None)
    after = getattr(candidate, "date_after", None)
    if before is None and hasattr(candidate, "date_pair") and isinstance(candidate.date_pair, dict):
        before = candidate.date_pair.get("before")
        after = candidate.date_pair.get("after")
    return _coerce_date(before), _coerce_date(after)


def _pair_days(candidate) -> int:
    """Compute actual time span between the two observations.

    The project intentionally avoids assuming fixed revisit spacing. For a
    monthly period observation, the effective score is still taken from the
    candidate itself but the interval is measured from the actual date bounds we
    have stored, or a minimum of one day if dates are missing.
    """
    before, after = _candidate_dates(candidate)
    if before is None or after is None:
        return 1
    if after >= before:
        return max((after - before).days, 1)
    return max((before - after).days, 1)


def _mean_effective_score_for_pairs(pairs: list) -> float | None:
    if not pairs:
        return None
    values = []
    for candidate in pairs:
        score, _ = _effective_score(candidate)
        values.append(score)
    return sum(values) / len(values)


def _midpoint_for_candidate(candidate):
    before, after = _candidate_dates(candidate)
    if before is None or after is None:
        return None
    return before + (after - before) / 2


def _observation_date(observation) -> datetime | None:
    if isinstance(observation, dict):
        if "acquisition_date" in observation:
            return _coerce_date(observation["acquisition_date"])
        if "date" in observation:
            return _coerce_date(observation["date"])
        if "date_after" in observation:
            return _coerce_date(observation["date_after"])
        if "date_before" in observation:
            return _coerce_date(observation["date_before"])
    return _coerce_date(getattr(observation, "acquisition_date", None) or getattr(observation, "date", None) or getattr(observation, "date_after", None) or getattr(observation, "date_before", None))


def _stage_label(index: int, count: int) -> str:
    if count == 1:
        return "CURRENT"
    if count == 2:
        return ["BEFORE", "CURRENT"][index]
    if count == 3:
        return ["BEFORE", "INTERMEDIATE", "CURRENT"][index]
    if count == 4:
        return ["BEFORE", "EARLY", "DEVELOPING", "CURRENT"][index]
    return ["BEFORE", "EARLY", "DEVELOPING", "LATE", "CURRENT"][index]


def select_temporal_keyframes(observations, pairwise_change_scores=None, velocity_series=None, image_paths=None):
    """Return a deterministic 1-5 frame selection from the real observation history.

    The selection keeps the extremal coverage points and the strongest transition
    when enough observations exist, without inventing data or duplicate dates.
    """
    ordered = list(observations or [])
    if not ordered:
        return []

    def normalize(item):
        if isinstance(item, dict):
            normalized = dict(item)
        else:
            normalized = {}
            for key in ("date", "acquisition_date", "date_before", "date_after", "tile_path", "sensor", "vector_id", "tile_id", "aoi_id", "cloud_fraction"):
                value = getattr(item, key, None)
                if value is not None:
                    normalized[key] = value
        normalized.setdefault("date", _frame_date(item))
        normalized.setdefault("acquisition_date", normalized.get("date"))
        return normalized

    normalized = [normalize(item) for item in ordered]
    if len(normalized) <= 5:
        selected = normalized
    else:
        metrics = [0.0] * len(normalized)
        if pairwise_change_scores:
            metrics = [abs(float(value)) for value in pairwise_change_scores[: len(normalized)]]
        elif velocity_series:
            metrics = [abs(float(value)) for value in velocity_series[: len(normalized)]]
        peak_index = max(range(len(normalized)), key=lambda idx: metrics[idx]) if metrics else 0
        indices = {0, len(normalized) - 1, peak_index}
        if len(normalized) >= 4:
            indices.add(len(normalized) // 3)
            indices.add((2 * len(normalized)) // 3)
        elif len(normalized) == 3:
            indices.add(1)
        selected = [normalized[idx] for idx in sorted(indices)]
        if len(selected) > 5:
            selected = [normalized[idx] for idx in sorted(set(indices) | {len(normalized) // 2})][:5]

    unique: list[dict] = []
    seen: set[str] = set()
    for item in selected:
        key = item.get("date") or item.get("acquisition_date") or repr(item)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    if len(unique) < min(5, len(normalized)):
        for item in normalized:
            key = item.get("date") or item.get("acquisition_date") or repr(item)
            if key in seen:
                continue
            unique.append(item)
            seen.add(key)
            if len(unique) >= min(5, len(normalized)):
                break
    return unique[: min(5, len(normalized))]


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
    first_midpoint = _midpoint_for_candidate(candidates[0])
    xs = []
    for candidate in candidates:
        score, source = _effective_score(candidate)
        days = _pair_days(candidate)
        velocity = score / max(days, 1)
        velocities.append(velocity)
        score_sources.append(source)
        midpoint = _midpoint_for_candidate(candidate)
        if midpoint is not None and first_midpoint is not None:
            xs.append((midpoint - first_midpoint).total_seconds() / 86400.0)
        else:
            xs.append(len(xs))
        series.append({
            "date_pair": {"before": getattr(candidate, "date_before", None), "after": getattr(candidate, "date_after", None)},
            "velocity": velocity,
            "source": source,
        })

    latest_velocity = velocities[-1] if velocities else None
    if len(velocities) >= 3:
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
    latest_mid = _midpoint_for_candidate(short_candidate)
    if latest_mid is not None:
        for candidate in candidates:
            candidate_mid = _midpoint_for_candidate(candidate)
            if candidate_mid is None:
                continue
            if candidate_mid.month == latest_mid.month:
                delta_days = abs((candidate_mid - latest_mid).days)
                if 275 <= delta_days <= 455:
                    seasonal_candidates.append(candidate)
            elif abs((candidate_mid - latest_mid).days) <= 45:
                seasonal_candidates.append(candidate)
    seasonal = _mean_effective_score_for_pairs(seasonal_candidates)
    seasonal_source = None
    if seasonal is not None and seasonal_candidates:
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
            if long_candidate is not None:
                long_score, long_source = _effective_score(long_candidate)

    if long_score is None:
        fallback_values = [_effective_score(candidate)[0] for candidate in candidates]
        if fallback_values:
            long_score = sum(fallback_values) / len(fallback_values)
        else:
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
    global _VELOCITY_CACHE
    now = monotonic()
    if _VELOCITY_CACHE and now - _VELOCITY_CACHE[0] < _VELOCITY_CACHE_TTL:
        return _VELOCITY_CACHE[1]
    tiles = db.get_all_tile_ids()
    results = {tile_id: compute_velocity(tile_id) for tile_id in tiles}
    _VELOCITY_CACHE = (now, results)
    return results
