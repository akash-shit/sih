"""Explainable optical spectral difference heatmaps."""
from pathlib import Path
import numpy as np
import rasterio
from PIL import Image
from app.config import DATA_DIR


def _band_index(source, names: tuple[str, ...], fallback: int | None) -> int | None:
    for index, description in enumerate(source.descriptions, start=1):
        text = (description or "").lower()
        if any(name in text for name in names):
            return index
    return fallback if fallback and fallback <= source.count else None


def spectral_diff_heatmap(before_path: str, after_path: str) -> str | None:
    try:
        with rasterio.open(before_path) as before, rasterio.open(after_path) as after:
            if before.shape != after.shape:
                return None
            red_b, nir_b = _band_index(before, ("red", "b04"), 3), _band_index(before, ("nir", "b08"), 4)
            red_a, nir_a = _band_index(after, ("red", "b04"), 3), _band_index(after, ("nir", "b08"), 4)
            if None in (red_b, nir_b, red_a, nir_a):
                return None
            red_before, nir_before = before.read([red_b, nir_b]).astype(np.float32)
            red_after, nir_after = after.read([red_a, nir_a]).astype(np.float32)
            stem = Path(after_path).stem

        def stretch(values: np.ndarray) -> np.ndarray:
            finite = values[np.isfinite(values)]
            if finite.size == 0:
                raise ValueError("no finite values")
            low, high = np.percentile(finite, [2, 98])
            return np.clip((values - low) / max(high - low, 1e-6), 0, 1)

        diff = (np.abs(stretch(red_after) - stretch(red_before)) + np.abs(stretch(nir_after) - stretch(nir_before))) / 2
        alpha = np.uint8(np.clip(diff, 0, 1) * 255)
        rgba = np.zeros((*alpha.shape, 4), dtype=np.uint8)
        rgba[..., 0], rgba[..., 3] = 255, alpha
        output = DATA_DIR / "generated" / "heatmaps" / f"{stem}.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgba, mode="RGBA").save(output)
        return str(output.relative_to(DATA_DIR.parent)).replace("\\", "/")
    except Exception:
        return None


def explainable_heatmaps(before: np.ndarray, after: np.ndarray, attention: np.ndarray | None = None) -> dict[str, str]:
    """Compatibility helper for array-based callers."""
    if before.shape != after.shape:
        raise ValueError("before and after arrays must have identical shapes")
    diff = np.abs(np.asarray(after, dtype=float) - np.asarray(before, dtype=float))
    if diff.ndim == 3:
        diff = np.nanmean(diff, axis=0)
    image = Image.fromarray(np.uint8(np.clip(diff / (np.nanmax(diff) + 1e-8), 0, 1) * 255), mode="L")
    import base64, io
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return {"spectral": "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")}
