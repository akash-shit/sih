"""
Stage 5 -- Remote-Sensing Features

These are NOT a replacement for the CLIP embedding -- they are the
complementary spectral evidence the architecture review called for
(3.2: OpenCLIP alone does not see NIR/SWIR). NDVI/NDWI give us a
physically-grounded second signal that feeds:
  - Stage 12 hybrid change scoring (spectral delta, not just embedding drift)
  - Stage 13 false-alarm suppression (cloud/water/snow fraction gating)

Band convention used throughout this project (matches tests/make_synthetic_scenes.py
and standard Sentinel-2 10m stacks): 1=B02(blue) 2=B03(green) 3=B04(red)
4=B08(NIR) 5=SCL (scene classification layer).
"""
from dataclasses import dataclass

import numpy as np
import rasterio

# Simplified Sentinel-2 SCL codes we care about for gating.
SCL_WATER = 6
SCL_CLOUD_MEDIUM_PROB = 8
SCL_CLOUD_HIGH_PROB = 9
SCL_THIN_CIRRUS = 10
SCL_SNOW = 11
SCL_CLOUD_CODES = {SCL_CLOUD_MEDIUM_PROB, SCL_CLOUD_HIGH_PROB, SCL_THIN_CIRRUS}


@dataclass
class TileFeatures:
    ndvi_mean: float
    ndvi_std: float
    ndwi_mean: float
    cloud_fraction: float | None
    snow_fraction: float | None
    water_fraction: float | None
    valid_pixel_fraction: float
    haze_score: float


def _safe_index(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """(a-b)/(a+b) with divide-by-zero guarded, standard for NDVI/NDWI."""
    denom = a + b
    out = np.zeros_like(denom, dtype=np.float32)
    nz = denom != 0
    out[nz] = (a[nz] - b[nz]) / denom[nz]
    return out


def compute_tile_features(tile_path: str) -> TileFeatures:
    with rasterio.open(tile_path) as src:
        blue, green, red, nir = src.read([1, 2, 3, 4]).astype(np.float32)
        scl = src.read(5) if src.count >= 5 else None
        nodata = src.nodata

    valid_mask = np.isfinite(blue) & np.isfinite(green) & np.isfinite(red) & np.isfinite(nir)
    valid_mask &= (blue != 0) & (green != 0) & (red != 0) & (nir != 0)
    if nodata is not None:
        valid_mask &= (blue != nodata) & (green != nodata) & (red != nodata) & (nir != nodata)

    ndvi = _safe_index(nir, red)
    ndwi = _safe_index(green, nir)  # McFeeters NDWI

    # Haze proxy: higher blue reflectance share plus lower visible contrast.
    visible_mean = (blue + green + red) / 3.0
    blue_fraction = blue / (blue + green + red + 1e-6)
    contrast = np.abs(visible_mean - np.nanmean(visible_mean[valid_mask])) if valid_mask.any() else np.zeros_like(visible_mean)
    haze_score = float(np.clip(
        np.nanmean(blue_fraction[valid_mask]) * 2.5 - np.nanmean(contrast[valid_mask]) * 2.0,
        0.0, 1.0,
    )) if valid_mask.any() else 0.0

    total_px = red.size
    valid_scl = scl is not None and np.all(np.isfinite(scl)) and np.all((scl >= 0) & (scl <= 11))
    cloud_fraction = float(np.isin(scl, list(SCL_CLOUD_CODES)).sum()) / total_px if valid_scl else None
    snow_fraction = float((scl == SCL_SNOW).sum()) / total_px if valid_scl else None
    water_fraction = float((scl == SCL_WATER).sum()) / total_px if valid_scl else None
    valid_pixel_fraction = float(valid_mask.sum()) / total_px

    return TileFeatures(
        ndvi_mean=float(np.nanmean(ndvi[valid_mask])) if valid_mask.any() else 0.0,
        ndvi_std=float(np.nanstd(ndvi[valid_mask])) if valid_mask.any() else 0.0,
        ndwi_mean=float(np.nanmean(ndwi[valid_mask])) if valid_mask.any() else 0.0,
        cloud_fraction=cloud_fraction,
        snow_fraction=snow_fraction,
        water_fraction=water_fraction,
        valid_pixel_fraction=valid_pixel_fraction,
        haze_score=haze_score,
    )
