"""Sentinel-1 backscatter features for GRD and monthly mosaic products.

This module intentionally computes backscatter-delta evidence only.  It does
not estimate interferometric coherence and does not resample SAR to the
optical grid.
"""
from dataclasses import dataclass
import logging
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import uniform_filter

from app.config import (
    SAR_APPLY_SPECKLE_FILTER,
    SAR_DIFF_SCALE,
    SAR_DIFF_WEIGHT,
    SAR_VH_DELTA_SCALE,
    SAR_VH_WEIGHT,
    SAR_VV_DELTA_SCALE,
    SAR_VV_WEIGHT,
)

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

