import numpy as np
import rasterio
from rasterio.transform import from_origin
from app.change.heatmap import spectral_diff_heatmap


def test_spectral_heatmap_returns_public_relative_png(tmp_path, monkeypatch):
    paths = []
    for index, value in enumerate((1.0, 2.0)):
        path = tmp_path / f"tile{index}.tif"
        profile = {"driver": "GTiff", "height": 2, "width": 2, "count": 4, "dtype": "float32", "transform": from_origin(0, 2, 10, 10)}
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(np.full((2, 2), value, dtype="float32"), 1)
            dst.write(np.full((2, 2), value, dtype="float32"), 2)
            dst.write(np.full((2, 2), value, dtype="float32"), 3)
            dst.write(np.full((2, 2), value * 2, dtype="float32"), 4)
        paths.append(str(path))
    assert spectral_diff_heatmap(paths[0], paths[1]).endswith(".png")
