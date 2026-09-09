"""
Stage 2 -- GeoTIFF / COG Reading

Responsibility: open a raw scene and report exactly what the computer
needs to know before anything else can happen -- dimensions, CRS,
geotransform, resolution, band count, nodata, and (if present) the
acquisition-date / sensor tags. Nothing here does tiling or ML; this is
purely "understand the file".
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import rasterio
from rasterio.crs import CRS


@dataclass
class SceneInfo:
    path: str
    width: int
    height: int
    band_count: int
    crs: str
    transform: tuple
    resolution_m: float
    nodata: Optional[float]
    dtype: str
    tags: dict = field(default_factory=dict)


def inspect_scene(scene_path: str) -> SceneInfo:
    """Open a scene and return its geospatial header info without
    loading full-resolution pixel data into memory."""
    path = Path(scene_path)
    if not path.exists():
        raise FileNotFoundError(f"Scene not found: {scene_path}")

    with rasterio.open(path) as src:
        # Sentinel-2 / Landsat pixels are usually square; take the x resolution.
        res_x = abs(src.transform.a)
        info = SceneInfo(
            path=str(path),
            width=src.width,
            height=src.height,
            band_count=src.count,
            crs=str(src.crs) if src.crs else "UNKNOWN",
            transform=tuple(src.transform)[:6],
            resolution_m=float(res_x),
            nodata=src.nodata,
            dtype=src.dtypes[0],
            tags=dict(src.tags()),
        )
    return info


def read_bands(scene_path: str, band_indexes: list[int], window=None) -> np.ndarray:
    """Read specific 1-indexed band numbers (rasterio convention) and
    return a (bands, height, width) float32 array. `window` is an
    optional rasterio.windows.Window to read only a sub-region, which
    is what the tiler uses so we never load a whole scene into RAM."""
    with rasterio.open(scene_path) as src:
        arr = src.read(band_indexes, window=window).astype(np.float32)
    return arr


def get_crs(scene_path: str) -> CRS:
    with rasterio.open(scene_path) as src:
        return src.crs
