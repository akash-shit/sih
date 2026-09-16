"""SAR ingestion and deterministic optical/SAR fusion helpers.

The implementation deliberately accepts simple numpy arrays so it works
offline and can be fed by Sentinel-1 GeoTIFF readers or test fixtures.
"""
from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np

@dataclass(frozen=True)
class SARObservation:
    path: str
    acquisition_date: str
    vv_mean: float
    vh_mean: float
    valid_fraction: float

def _normalised_delta(before: np.ndarray, after: np.ndarray) -> float:
    b, a = np.asarray(before, dtype=float), np.asarray(after, dtype=float)
    mask = np.isfinite(b) & np.isfinite(a) & (b != 0) & (a != 0)
    if not mask.any():
        return 0.0
    # SAR is commonly stored in dB; an absolute dB delta is stable and
    # bounded for scoring after normalisation.
    return float(np.clip(np.nanmedian(np.abs(a[mask] - b[mask])) / 10.0, 0.0, 1.0))

def sar_change_score(vv_before, vv_after, vh_before, vh_after, diff_before=None, diff_after=None) -> float:
    """Return a [0,1] SAR change score from VV/VH and optional difference signal."""
    vv = _normalised_delta(vv_before, vv_after)
    vh = _normalised_delta(vh_before, vh_after)
    difference_signal = _normalised_delta(diff_before, diff_after) if diff_before is not None and diff_after is not None else 0.0
    return float(np.clip(0.45 * vv + 0.35 * vh + 0.20 * difference_signal, 0.0, 1.0))

def fuse_modalities(optical_score: float, sar_score: float | None, *, sar_only: bool = False) -> float:
    """Fuse scores while retaining an explicit SAR-only path."""
    optical = float(np.clip(optical_score, 0.0, 1.0))
    if sar_score is None:
        return optical
    sar = float(np.clip(sar_score, 0.0, 1.0))
    return float(np.clip((0.40 * sar if sar_only else 0.55 * optical + 0.45 * sar), 0.0, 1.0))

def ingest_sar_manifest(path: str | Path) -> list[SARObservation]:
    """Read a JSON manifest (list or ``{"observations": [...]}``) safely."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("observations", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("SAR manifest must contain a list of observations")
    result = []
    for row in rows:
        result.append(SARObservation(str(row["path"]), str(row["acquisition_date"]),
                                     float(row.get("vv_mean", 0)), float(row.get("vh_mean", 0)),
                                     float(row.get("valid_fraction", 1))))
    return result

def observation_from_raster(path: str | Path, acquisition_date: str) -> SARObservation:
    """Summarise a VV/VH GeoTIFF without requiring a SAR SDK.

    Bands 1 and 2 are interpreted as VV and VH. Invalid pixels are excluded,
    preserving source provenance for later tile-level matching.
    """
    import rasterio
    with rasterio.open(path) as src:
        if src.count < 2:
            raise ValueError("SAR raster must contain VV and VH bands")
        vv, vh = src.read([1, 2]).astype(np.float32)
    valid = np.isfinite(vv) & np.isfinite(vh) & (vv != 0) & (vh != 0)
    fraction = float(valid.mean())
    if not valid.any():
        raise ValueError(f"SAR raster has no valid VV/VH pixels: {path}")
    return SARObservation(str(path), acquisition_date, float(np.nanmean(vv[valid])),
                          float(np.nanmean(vh[valid])), fraction)
