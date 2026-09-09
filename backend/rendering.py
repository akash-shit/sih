import hashlib
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

from app.config import TILE_SIZE_PX
from app.geospatial.rendering import true_color_image


RENDER_VERSION = "rgb-v2"


def _rgb(tile_path: str) -> Image.Image:
    return true_color_image(tile_path)


def tile_thumbnail(tile_path: str, output_dir: Path, vector_id: int) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"tile-{vector_id}-{RENDER_VERSION}.png"
    if not output_path.exists():
        _rgb(tile_path).save(output_path, format="PNG")
    return output_path


def mosaic_thumbnail(rows: list, output_dir: Path, cache_key: str) -> tuple[Path, int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_id = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()[:16]
    output_path = output_dir / f"mosaic-{cache_id}-{RENDER_VERSION}.png"
    width = (max((int(row["col_idx"] or 0) for row in rows), default=0) + 1) * TILE_SIZE_PX
    height = (max((int(row["row_idx"] or 0) for row in rows), default=0) + 1) * TILE_SIZE_PX
    if not output_path.exists():
        canvas = Image.new("RGB", (width, height))
        for row in rows:
            tile = _rgb(row["tile_path"])
            canvas.paste(tile, (int(row["col_idx"] or 0) * TILE_SIZE_PX, int(row["row_idx"] or 0) * TILE_SIZE_PX))
        canvas.save(output_path, format="PNG")
    return output_path, width, height


def compute_pixel_change_map(before_path: str, after_path: str, output_dir: Path, cache_key: str) -> tuple[Path, float, str | None, float | None, float | None]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_id = hashlib.sha256(f"{RENDER_VERSION}:{cache_key}".encode("utf-8")).hexdigest()[:16]
    output_path = output_dir / f"difference-{cache_id}-{RENDER_VERSION}.png"
    before = np.asarray(_rgb(before_path), dtype=np.float32) / 255.0
    after = np.asarray(_rgb(after_path), dtype=np.float32) / 255.0
    valid = np.isfinite(before).all(axis=2) & np.isfinite(after).all(axis=2)
    valid &= before.max(axis=2) > 0
    valid &= after.max(axis=2) > 0
    matched_after = after.copy()
    for channel in range(3):
        before_values = before[..., channel][valid]
        after_values = after[..., channel][valid]
        if before_values.size and after_values.size and np.std(after_values) > 1e-6:
            matched_after[..., channel][valid] = (
                (after_values - np.mean(after_values)) * np.std(before_values) / np.std(after_values)
                + np.mean(before_values)
            ).clip(0.0, 1.0)
    delta = np.abs(matched_after - before).mean(axis=2)
    valid_delta = delta[valid]
    if valid_delta.size:
        threshold = float(np.mean(valid_delta) + 2.0 * np.std(valid_delta))
        changed = valid & (delta > threshold)
    else:
        changed = np.zeros(delta.shape, dtype=bool)
    if not output_path.exists():
        heatmap = np.zeros((*delta.shape, 4), dtype=np.uint8)
        heatmap[..., 0] = np.where(changed, 255, 0)
        heatmap[..., 1] = np.where(changed, (delta * 120).clip(0, 120), 0).astype(np.uint8)
        heatmap[..., 3] = np.where(changed, 190, 0).astype(np.uint8)
        Image.fromarray(heatmap, mode="RGBA").save(output_path, format="PNG")
    if not changed.any():
        region = None
        centroid_x = centroid_y = None
    else:
        ys, xs = np.where(changed)
        region = f"x={xs.min()}..{xs.max()}, y={ys.min()}..{ys.max()}"
        centroid_x = float(xs.mean())
        centroid_y = float(ys.mean())
    return output_path, float(changed.mean()), region, centroid_x, centroid_y


def difference_image(before_path: str, after_path: str, output_dir: Path, cache_key: str):
    return compute_pixel_change_map(before_path, after_path, output_dir, cache_key)
