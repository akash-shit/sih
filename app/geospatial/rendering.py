from pathlib import Path

import numpy as np
import rasterio
from PIL import Image


def _stretch_channel(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    if int(valid.sum()) < 16:
        return np.zeros(values.shape, dtype=np.uint8)
    low, high = np.percentile(values[valid], (2, 98))
    if float(high - low) < 1e-6:
        return np.zeros(values.shape, dtype=np.uint8)
    return (np.clip((values - low) / float(high - low), 0, 1) * 255).astype(np.uint8)


def true_color_image(tile_path: str | Path) -> Image.Image:
    """Render B04/B03/B02 with independent valid-pixel percentile stretches."""
    with rasterio.open(tile_path) as source:
        masked = source.read([3, 2, 1], masked=True)
        bands = masked.filled(0).astype(np.float32)
        masks = np.ma.getmaskarray(masked)
    channels = []
    for index in range(3):
        valid = ~masks[index] & np.isfinite(bands[index]) & (bands[index] != 0)
        channels.append(_stretch_channel(bands[index], valid))
    return Image.fromarray(np.stack(channels, axis=-1), mode="RGB")


def has_valid_multispectral_data(scene_path: str | Path) -> bool:
    """Return whether all required Sentinel bands contain real pixels."""
    with rasterio.open(scene_path) as source:
        if source.count < 4:
            return False
        bands = source.read([1, 2, 3, 4], masked=True)
    for band in bands:
        values = band.compressed()
        if values.size == 0 or not np.isfinite(values).any() or not np.any(values != 0):
            return False
    return True