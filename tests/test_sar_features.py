import numpy as np
import rasterio
from rasterio.transform import from_origin
from app.geospatial.sar_features import compute_sar_features, sar_change_score, SarFeatures


def test_sar_features_convert_linear_values(tmp_path):
    path = tmp_path / "sar.tif"
    profile = {"driver": "GTiff", "height": 2, "width": 2, "count": 3, "dtype": "float32", "transform": from_origin(0, 2, 20, 20)}
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(np.full((2, 2), 0.1, dtype="float32"), 1)
        dst.write(np.full((2, 2), 0.05, dtype="float32"), 2)
        dst.write(np.ones((2, 2), dtype="float32"), 3)
    result = compute_sar_features(str(path))
    assert result.vv_mean_db is not None and result.vv_mean_db < -9
    assert result.valid_pixels == 1.0
    assert sar_change_score(SarFeatures(-10, -15, 1, 1, 5, 1), SarFeatures(-8, -14, 1, 1, 6, 1)) > 0
