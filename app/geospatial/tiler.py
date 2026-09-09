"""
Stage 3 -- Tiling
Stage 4 -- Common Grid / Normalization (CRS + resampling handled by
           always reading through the same fixed-size window logic)

Design note (Refinement 3.1 from the architecture review):
MGRS gives every tile a STABLE SPATIAL IDENTIFIER so the same ground
footprint is easy to find again across dates -- it is a lookup key,
not a claim of pixel-perfect co-registration. Real sub-pixel alignment
is out of scope for the prototype; we accept the coarser guarantee
that "same tile_id" == "same ~2.24 km ground cell", and rely on the
quality/confound checks in Stage 13 to catch anything registration
error introduces.

Each tile is written out as its own small GeoTIFF (so later stages
can reopen just a tile instead of the whole scene) and returns a
dataclass with everything the SQLite layer needs to store.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.warp import transform as warp_transform
import mgrs as mgrs_lib

from app.config import TILE_SIZE_PX, TILES_DIR

_MGRS = mgrs_lib.MGRS()


@dataclass
class Tile:
    tile_id: str          # MGRS-based stable ground identifier
    scene_path: str
    tile_path: str
    row: int
    col: int
    bbox_wgs84: tuple     # (minlon, minlat, maxlon, maxlat)
    acquisition_date: str
    sensor: str


def _pixel_center_lonlat(src, row: int, col: int, tile_px: int):
    """Center of a tile window, transformed from the scene's CRS to WGS84
    so we can compute a real-world MGRS reference for it."""
    cx_px = col * tile_px + tile_px / 2
    cy_px = row * tile_px + tile_px / 2
    x, y = rasterio.transform.xy(src.transform, cy_px, cx_px)
    lon, lat = warp_transform(src.crs, "EPSG:4326", [x], [y])
    return lon[0], lat[0]


def tile_scene(scene_path: str, acquisition_date: str, sensor: str,
               tile_px: int = TILE_SIZE_PX) -> list[Tile]:
    """Split one scene into non-overlapping tile_px x tile_px tiles.
    Every tile gets an MGRS id derived from its center coordinate, so a
    tile covering the same ground in a later date resolves to the same
    id (Stage 11 temporal pairing groups on exactly this key)."""
    scene_path = Path(scene_path)
    tiles: list[Tile] = []

    with rasterio.open(scene_path) as src:
        n_rows = src.height // tile_px
        n_cols = src.width // tile_px

        for row in range(n_rows):
            for col in range(n_cols):
                window = Window(col * tile_px, row * tile_px, tile_px, tile_px)
                data = src.read(window=window)

                # Skip tiles that are entirely nodata (edge of AOI).
                if src.nodata is not None and np.all(data == src.nodata):
                    continue

                lon, lat = _pixel_center_lonlat(src, row, col, tile_px)
                tile_id = _MGRS.toMGRS(lat, lon, MGRSPrecision=3)  # ~100m precision cell

                out_transform = rasterio.windows.transform(window, src.transform)
                out_name = f"{tile_id}_{acquisition_date}.tif"
                out_path = TILES_DIR / out_name

                with rasterio.open(
                    out_path, "w", driver="GTiff",
                    height=tile_px, width=tile_px, count=src.count,
                    dtype=data.dtype, crs=src.crs, transform=out_transform,
                    nodata=src.nodata,
                ) as dst:
                    dst.write(data)

                # bbox in WGS84 for the map UI later
                b = rasterio.windows.bounds(window, src.transform)
                (minlon, minlat), (maxlon, maxlat) = (
                    warp_transform(src.crs, "EPSG:4326", [b[0]], [b[1]])[:2],
                    warp_transform(src.crs, "EPSG:4326", [b[2]], [b[3]])[:2],
                )

                tiles.append(Tile(
                    tile_id=tile_id,
                    scene_path=str(scene_path),
                    tile_path=str(out_path),
                    row=row, col=col,
                    bbox_wgs84=(minlon[0], minlat[0], maxlon[0], maxlat[0]),
                    acquisition_date=acquisition_date,
                    sensor=sensor,
                ))

    return tiles
