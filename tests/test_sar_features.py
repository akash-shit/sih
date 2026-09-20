import numpy as np
import rasterio
from types import SimpleNamespace
from rasterio.transform import from_origin
from app.geospatial.sar_features import (
    compute_sar_features, find_matching_sar_pair, sar_change_score, SarFeatures,
    is_supported_sar_source,
)
from app.geospatial import catalog_db
from app.cli import cmd_ingest_sar


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


def test_synthetic_raster_registration_and_fusion(tmp_path, monkeypatch):
    monkeypatch.setattr(catalog_db, "DB_PATH", tmp_path / "catalog.sqlite3")
    catalog_db.init_db()
    for name, vv_value, acquisition_date in (
        ("before.tif", 0.10, "2025-01-01"),
        ("after.tif", 0.20, "2025-01-20"),
    ):
        path = tmp_path / name
        profile = {"driver": "GTiff", "height": 2, "width": 2, "count": 3,
                   "dtype": "float32", "transform": from_origin(0, 2, 20, 20)}
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(np.full((2, 2), vv_value, dtype="float32"), 1)
            dst.write(np.full((2, 2), vv_value / 2, dtype="float32"), 2)
            dst.write(np.ones((2, 2), dtype="float32"), 3)
        cmd_ingest_sar(SimpleNamespace(
            raster=str(path), tile_id="T-1", product_type="GRD", sensor="SENTINEL1",
            aoi_id=None, date=acquisition_date, period_start=None, period_end=None,
            acquisition_datetime=None,
        ))
    pair = find_matching_sar_pair(
        {"tile_id": "T-1", "acquisition_date": "2025-01-01"},
        {"tile_id": "T-1", "acquisition_date": "2025-01-20"},
    )
    assert pair is not None
    assert sar_change_score(*pair) > 0


def test_sar_source_filter_rejects_raw_and_ratio_products():
    assert is_supported_sar_source("S1A_IW_VV.tif")
    assert is_supported_sar_source("S1A_IW_VH.tif")
    assert not is_supported_sar_source("S1A_IW_RGB_Ratio.tif")
    assert not is_supported_sar_source("S1A_IW_VV_(Raw).tif")
    assert not is_supported_sar_source("S1A_IW_VH_(Raw).tif")
    assert not is_supported_sar_source("SAR_Urban.tif")
