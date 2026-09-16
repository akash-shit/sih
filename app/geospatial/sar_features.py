"""Sentinel-1 backscatter features for GRD and monthly mosaic products.

This module intentionally computes backscatter-delta evidence only.  It does
not estimate interferometric coherence and does not resample SAR to the
optical grid.
"""
from dataclasses import dataclass
import logging
from datetime import date, datetime
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import uniform_filter

from app.config import (
    SAR_APPLY_SPECKLE_FILTER,
    SAR_DIFF_SCALE,
    SAR_DIFF_WEIGHT,
    SAR_OPTICAL_MATCH_TOLERANCE_DAYS,
    SAR_VH_DELTA_SCALE,
    SAR_VH_WEIGHT,
    SAR_VV_DELTA_SCALE,
    SAR_VV_WEIGHT,
)
from app.geospatial import catalog_db as db

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SarFeatures:
    vv_mean_db: float | None
    vh_mean_db: float | None
    vv_std_db: float | None
    vh_std_db: float | None
    vv_minus_vh_db: float | None
    valid_pixels: float
    speckle_filter_applied: bool = False


def _coerce_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _row_to_features(row) -> SarFeatures:
    return SarFeatures(
        vv_mean_db=row["vv_mean_db"],
        vh_mean_db=row["vh_mean_db"],
        vv_std_db=row["vv_std_db"],
        vh_std_db=row["vh_std_db"],
        vv_minus_vh_db=row["vv_minus_vh_db"],
        valid_pixels=float(row["valid_pixels"] or 0.0),
        speckle_filter_applied=bool(row["speckle_filter_applied"]),
    )


def _match_distance(row, target_date, product_type: str) -> int | None:
    candidate_date = _coerce_date(target_date)
    if candidate_date is None:
        return None
    if product_type == "GRD":
        observation_date = _coerce_date(row.get("acquisition_datetime") or row.get("period_start") or row.get("period_end"))
        if observation_date is None:
            return None
        distance = abs((observation_date - candidate_date).days)
        return distance if distance <= SAR_OPTICAL_MATCH_TOLERANCE_DAYS else None
    if product_type == "IW_MONTHLY_MOSAIC":
        period_start = _coerce_date(row.get("period_start") or row.get("acquisition_datetime"))
        period_end = _coerce_date(row.get("period_end") or row.get("acquisition_datetime"))
        if period_start and period_end and period_start <= candidate_date <= period_end:
            return 0
        if period_start and period_start.year == candidate_date.year and period_start.month == candidate_date.month:
            return 0
        if period_end and period_end.year == candidate_date.year and period_end.month == candidate_date.month:
            return 0
        observation_date = _coerce_date(row.get("acquisition_datetime"))
        if observation_date and observation_date.year == candidate_date.year and observation_date.month == candidate_date.month:
            return 0
    return None


def _best_sar_match(rows, target_date) -> tuple[str, SarFeatures] | None:
    candidate_date = _coerce_date(target_date)
    if candidate_date is None:
        return None
    best: tuple[int, str, SarFeatures] | None = None
    for row in rows:
        product_type = str(row.get("product_type") or "").upper()
        if not product_type:
            continue
        distance = _match_distance(row, candidate_date, product_type)
        if distance is None:
            continue
        if product_type not in {"GRD", "IW_MONTHLY_MOSAIC"}:
            continue
        if best is None or distance < best[0]:
            best = (distance, product_type, _row_to_features(row))
    if best is None:
        return None
    return best[1], best[2]


def find_matching_sar_pair(before_row, after_row) -> tuple[SarFeatures, SarFeatures] | None:
    """Return the SAR features that match a before/after optical pair.

    The matched SAR observations must be compatible by product type: GRD and
    monthly mosaic products are never mixed in the same fused pair.
    """
    if before_row is None or after_row is None:
        return None
    if (before_row.get("tile_id") if hasattr(before_row, "get") else before_row["tile_id"]) != (after_row.get("tile_id") if hasattr(after_row, "get") else after_row["tile_id"]):
        return None
    tile_id = before_row.get("tile_id") if hasattr(before_row, "get") else before_row["tile_id"]
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sar_tiles WHERE tile_id = ? ORDER BY acquisition_datetime ASC, period_start ASC",
            (tile_id,),
        ).fetchall()
    before_match = _best_sar_match(rows, before_row["acquisition_date"])
    after_match = _best_sar_match(rows, after_row["acquisition_date"])
    if before_match is None or after_match is None or before_match[0] != after_match[0]:
        return None
    return before_match[1], after_match[1]


def _is_linear(tags: dict[str, str], values: np.ndarray) -> bool:
    text = " ".join(f"{k}={v}" for k, v in tags.items()).lower()
    if any(token in text for token in ("decibel", " db", "unit=db", "units=db")):
        return False
    if any(token in text for token in ("linear", "gamma0", "power")):
        return True
    heuristic = float(np.nanmedian(values)) if np.isfinite(values).any() else 0.0
    logger.info("SAR units metadata unavailable; median heuristic selected %s input", "linear" if heuristic < 0.5 else "dB")
    return heuristic < 0.5


def _lee_filter(values: np.ndarray, size: int = 5) -> np.ndarray:
    local_mean = uniform_filter(values, size=size, mode="nearest")
    local_sq = uniform_filter(values * values, size=size, mode="nearest")
    variance = np.maximum(local_sq - local_mean * local_mean, 0)
    noise = float(np.nanmedian(variance))
    weight = variance / (variance + noise + 1e-8)
    return local_mean + weight * (values - local_mean)


def _summary(values: np.ndarray, mask: np.ndarray) -> tuple[float | None, float | None]:
    selected = values[mask]
    if selected.size == 0:
        return None, None
    return float(np.mean(selected)), float(np.std(selected))


def compute_sar_features(sar_tile_path: str) -> SarFeatures:
    with rasterio.open(sar_tile_path) as source:
        vv = source.read(1).astype(np.float32)
        vh = source.read(2).astype(np.float32) if source.count >= 2 else None
        data_mask = source.read(3) if source.count >= 3 else None
        tags = {**source.tags(), **source.tags(1)}
        if vh is not None:
            tags.update(source.tags(2))
        transform_to_db = _is_linear(tags, vv)

    if transform_to_db:
        vv = 10.0 * np.log10(np.maximum(vv, 1e-10))
        if vh is not None:
            vh = 10.0 * np.log10(np.maximum(vh, 1e-10))
        logger.info("Converted SAR linear backscatter to dB")
    else:
        logger.info("SAR metadata indicates dB backscatter")
    if vh is None:
        return SarFeatures(None, None, None, None, None, 0.0, False)
    if SAR_APPLY_SPECKLE_FILTER:
        vv, vh = _lee_filter(vv), _lee_filter(vh)
    mask = np.isfinite(vv) & np.isfinite(vh) & (vv != 0) & (vh != 0) & (vv >= -30) & (vh >= -30)
    if data_mask is not None:
        mask &= data_mask != 0
    valid_fraction = float(mask.mean()) if mask.size else 0.0
    vv_mean, vv_std = _summary(vv, mask)
    vh_mean, vh_std = _summary(vh, mask)
    difference = vv - vh
    diff_mean = float(np.mean(difference[mask])) if mask.any() else None
    return SarFeatures(vv_mean, vh_mean, vv_std, vh_std, diff_mean, valid_fraction, SAR_APPLY_SPECKLE_FILTER)


def _scaled(delta: float | None, scale: float) -> float:
    return 0.0 if delta is None else float(np.clip(abs(delta) / scale, 0.0, 1.0))


def sar_change_score(before: SarFeatures, after: SarFeatures) -> float:
    """Score VV/VH backscatter change; prototype weights require real-data validation."""
    return float(np.clip(
        SAR_VV_WEIGHT * _scaled(
            None if before.vv_mean_db is None or after.vv_mean_db is None else after.vv_mean_db - before.vv_mean_db,
            SAR_VV_DELTA_SCALE,
        )
        + SAR_VH_WEIGHT * _scaled(
            None if before.vh_mean_db is None or after.vh_mean_db is None else after.vh_mean_db - before.vh_mean_db,
            SAR_VH_DELTA_SCALE,
        )
        + SAR_DIFF_WEIGHT * _scaled(
            None if before.vv_minus_vh_db is None or after.vv_minus_vh_db is None else after.vv_minus_vh_db - before.vv_minus_vh_db,
            SAR_DIFF_SCALE,
        ), 0.0, 1.0))

