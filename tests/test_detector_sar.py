import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.change import detector
from app.change.adaptive import adaptive_score
from app.geospatial import catalog_db
from app.geospatial.sar_features import SarFeatures, sar_change_score, compute_sar_features


def test_sar_score_is_independent_of_optical_when_valid():
    before = SarFeatures(-12, -18, 1, 1, 6, 1)
    after = SarFeatures(-8, -14, 1, 1, 6, 1)
    assert 0 < sar_change_score(before, after) <= 1


def _optical_row(vector_id, date):
    return {
        "tile_id": "T-1", "vector_id": vector_id, "acquisition_date": date,
        "tile_path": "unused.tif", "cloud_fraction": 0.0,
        "valid_pixel_fraction": 1.0, "haze_score": 0.0, "snow_fraction": 0.0,
        "ndvi_mean": 0.2, "ndwi_mean": 0.1, "land_cover": "cropland",
    }


def test_timeline_uses_real_sar_tiles_for_fusion(tmp_path, monkeypatch):
    monkeypatch.setattr(catalog_db, "DB_PATH", tmp_path / "catalog.sqlite3")
    catalog_db.init_db()
    for name, vv, date in (("before.tif", 0.1, "2025-01-01"), ("after.tif", 0.3, "2025-01-20")):
        path = tmp_path / name
        profile = {"driver": "GTiff", "height": 2, "width": 2, "count": 2,
                   "dtype": "float32", "transform": from_origin(0, 2, 20, 20)}
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(np.full((2, 2), vv, dtype="float32"), 1)
            dst.write(np.full((2, 2), vv / 2, dtype="float32"), 2)
        catalog_db.register_sar_tile(
            tile_id="T-1", tile_path=str(path), features=compute_sar_features(str(path)),
            product_type="GRD", acquisition_datetime=date,
        )

    rows = [_optical_row(1, "2025-01-01"), _optical_row(2, "2025-01-20")]
    monkeypatch.setattr(detector.db, "get_tile_history", lambda tile_id: rows)
    monkeypatch.setattr(detector, "_quality_gate", lambda before, after: None)

    class FakeIndex:
        def has_vector(self, vector_id):
            return True

        def get_vector(self, vector_id):
            return np.array([1.0, 0.0]) if vector_id == 1 else np.array([0.0, 1.0])

    monkeypatch.setattr(detector, "VectorIndex", FakeIndex)
    candidates = detector.analyze_tile_timeline("T-1", threshold=0.0)
    assert len(candidates) == 1
    assert candidates[0].modality != "optical_only"


def test_timeline_without_sar_preserves_optical_score(monkeypatch):
    rows = [_optical_row(1, "2025-01-01"), _optical_row(2, "2025-01-20")]
    monkeypatch.setattr(detector.db, "get_tile_history", lambda tile_id: rows)
    monkeypatch.setattr(detector, "_quality_gate", lambda before, after: None)
    monkeypatch.setattr(detector, "find_matching_sar_pair", lambda before, after: None)

    class FakeIndex:
        def has_vector(self, vector_id):
            return True

        def get_vector(self, vector_id):
            return np.array([1.0, 0.0]) if vector_id == 1 else np.array([0.8, 0.6])

    monkeypatch.setattr(detector, "VectorIndex", FakeIndex)
    candidate = detector.analyze_tile_timeline("T-1", threshold=0.0)[0]
    expected = adaptive_score(
        candidate.embedding_drift, candidate.spectral_delta, land_cover="cropland"
    )
    assert candidate.combined_score == expected
    assert candidate.modality == "optical_only"
