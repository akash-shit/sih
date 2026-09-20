from datetime import datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.change.temporal_signature import (
    _effective_score,
    compute_velocity,
    select_temporal_keyframes,
    temporal_profile,
)
from backend.main import app


def test_effective_score_prefers_fused_and_sar_only():
    fused = SimpleNamespace(combined_score=0.60, fused_score=0.90, sar_only=False)
    assert _effective_score(fused) == (0.9, "fused")

    rescued = SimpleNamespace(combined_score=0.80, sar_only=True)
    assert _effective_score(rescued) == (0.8, "sar_only")

    optical = SimpleNamespace(combined_score=0.40, sar_only=False)
    assert _effective_score(optical) == (0.4, "combined")


def test_velocity_uses_uneven_spacing_and_reports_trend(monkeypatch):
    candidate_pairs = [
        SimpleNamespace(
            tile_id="T123",
            date_before="2025-01-01",
            date_after="2025-01-15",
            combined_score=0.10,
            sar_only=False,
            fused_score=None,
            score_source="combined",
        ),
        SimpleNamespace(
            tile_id="T123",
            date_before="2025-02-01",
            date_after="2025-02-10",
            combined_score=0.30,
            sar_only=False,
            fused_score=None,
            score_source="combined",
        ),
        SimpleNamespace(
            tile_id="T123",
            date_before="2025-03-01",
            date_after="2025-03-20",
            combined_score=0.70,
            sar_only=False,
            fused_score=None,
            score_source="combined",
        ),
    ]

    monkeypatch.setattr(
        "app.change.temporal_signature.analyze_tile_timeline",
        lambda tile_id, threshold=0.0: candidate_pairs,
    )

    result = compute_velocity("T123")
    assert result.tile_id == "T123"
    assert result.latest_velocity is not None
    assert result.trend in {"steady_change", "accelerating", "stable"}
    assert len(result.velocities) == 3
    assert result.score_sources == ["combined", "combined", "combined"]


def test_temporal_profile_uses_first_to_last_comparison(monkeypatch):
    candidates = [
        SimpleNamespace(date_before="2025-01-01", date_after="2025-02-01", combined_score=0.2, sar_only=False, fused_score=None),
        SimpleNamespace(date_before="2025-02-01", date_after="2025-03-01", combined_score=0.8, sar_only=False, fused_score=None),
    ]
    history = [
        {"vector_id": 1, "acquisition_date": "2025-01-01"},
        {"vector_id": 2, "acquisition_date": "2025-02-01"},
        {"vector_id": 3, "acquisition_date": "2025-03-01"},
    ]
    long_candidate = SimpleNamespace(combined_score=0.35, sar_only=False, fused_score=None)
    monkeypatch.setattr("app.change.temporal_signature.analyze_tile_timeline", lambda tile_id, threshold=0.0: candidates)
    monkeypatch.setattr("app.change.temporal_signature.analyze_tile_pair", lambda first, last: long_candidate)
    monkeypatch.setattr("app.change.temporal_signature.VectorIndex.has_vector", lambda self, vector_id: True)
    monkeypatch.setattr("app.change.temporal_signature.db.get_tile_history", lambda tile_id: history)

    profile = temporal_profile("T123")

    assert profile["long"] == 0.35
    assert profile["long"] != profile["short"]
    assert profile["score_sources"]["long"] == "combined"


def test_temporal_profile_handles_two_rows_and_missing_vectors(monkeypatch):
    candidate = SimpleNamespace(date_before="2025-01-01", date_after="2025-02-01", combined_score=0.4, sar_only=False, fused_score=None)
    monkeypatch.setattr("app.change.temporal_signature.analyze_tile_timeline", lambda tile_id, threshold=0.0: [candidate])
    monkeypatch.setattr("app.change.temporal_signature.db.get_tile_history", lambda tile_id: [{"vector_id": 1}, {"vector_id": 2}])
    monkeypatch.setattr("app.change.temporal_signature.VectorIndex.has_vector", lambda self, vector_id: False)

    profile = temporal_profile("T123")

    assert profile["long"] == profile["short"] == 0.4
    assert profile["score_sources"]["long"] == "combined_fallback_no_direct_comparison"


def test_change_velocity_contract_exposes_series(monkeypatch):
    client = TestClient(app)

    fake_results = {
        "T1": SimpleNamespace(
            trend="steady_change",
            latest_velocity=0.12,
            acceleration=0.03,
            series=[
                {
                    "date_pair": {"before": "2025-01-01", "after": "2025-01-15"},
                    "velocity": 0.1,
                    "source": "combined",
                }
            ],
            velocities=[0.1, 0.2],
        )
    }
    monkeypatch.setattr("backend.main.temporal_signature.velocity_for_all_tiles", lambda: fake_results)

    response = client.get("/changes/velocity")
    assert response.status_code == 200
    payload = response.json()
    assert payload and "series" in payload[0]
    assert payload[0]["series"][0]["date_pair"]["before"] == "2025-01-01"
    assert payload[0]["series"][0]["velocity"] == 0.1
    assert payload[0]["series"][0]["source"] == "combined"


def test_change_velocity_supports_page_limits_and_offset(monkeypatch):
    client = TestClient(app)
    fake_results = {
        "T1": SimpleNamespace(trend="stable", latest_velocity=0.1, acceleration=0.0, series=[{"date_pair": {"before": "2025-01-01", "after": "2025-01-15"}, "velocity": 0.1, "source": "combined"}], velocities=[0.1]),
        "T2": SimpleNamespace(trend="accelerating", latest_velocity=0.2, acceleration=0.1, series=[{"date_pair": {"before": "2025-01-01", "after": "2025-01-15"}, "velocity": 0.2, "source": "combined"}], velocities=[0.2]),
        "T3": SimpleNamespace(trend="steady_change", latest_velocity=0.3, acceleration=0.2, series=[{"date_pair": {"before": "2025-01-01", "after": "2025-01-15"}, "velocity": 0.3, "source": "combined"}], velocities=[0.3]),
    }
    monkeypatch.setattr("backend.main.temporal_signature.velocity_for_all_tiles", lambda: fake_results)

    response = client.get("/changes/velocity", params={"limit": 2, "offset": 1})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert [item["tile_id"] for item in payload] == ["T3", "T1"]


def test_select_temporal_keyframes_prefers_earliest_peak_latest_and_keeps_determinism():
    history = [
        {"vector_id": 1, "acquisition_date": "2020-01-01", "tile_path": "/tmp/1.tif", "sensor": "SENTINEL2"},
        {"vector_id": 2, "acquisition_date": "2020-04-01", "tile_path": "/tmp/2.tif", "sensor": "SENTINEL2"},
        {"vector_id": 3, "acquisition_date": "2021-01-01", "tile_path": "/tmp/3.tif", "sensor": "SENTINEL2"},
        {"vector_id": 4, "acquisition_date": "2022-01-01", "tile_path": "/tmp/4.tif", "sensor": "SENTINEL2"},
        {"vector_id": 5, "acquisition_date": "2024-01-01", "tile_path": "/tmp/5.tif", "sensor": "SENTINEL2"},
    ]
    frames = select_temporal_keyframes(history)
    assert [frame["date"] for frame in frames] == [
        "2020-01-01",
        "2020-04-01",
        "2021-01-01",
        "2022-01-01",
        "2024-01-01",
    ]
    assert len(frames) == 5


def test_temporal_evolution_endpoint_uses_real_tile_frames(monkeypatch):
    client = TestClient(app)
    history = [
        {"vector_id": 10, "tile_id": "T9", "aoi_id": 1, "acquisition_date": "2020-01-01", "tile_path": "/tmp/a.tif", "sensor": "SENTINEL2", "cloud_fraction": 0.01, "minlat": 0.0, "maxlat": 1.0, "minlon": 0.0, "maxlon": 1.0},
        {"vector_id": 11, "tile_id": "T9", "aoi_id": 1, "acquisition_date": "2021-01-01", "tile_path": "/tmp/b.tif", "sensor": "SENTINEL2", "cloud_fraction": 0.02, "minlat": 0.0, "maxlat": 1.0, "minlon": 0.0, "maxlon": 1.0},
        {"vector_id": 12, "tile_id": "T9", "aoi_id": 1, "acquisition_date": "2023-01-01", "tile_path": "/tmp/c.tif", "sensor": "SENTINEL2", "cloud_fraction": 0.03, "minlat": 0.0, "maxlat": 1.0, "minlon": 0.0, "maxlon": 1.0},
    ]
    monkeypatch.setattr("backend.main.db.get_tile_history", lambda tile_id: history)
    monkeypatch.setattr("backend.main.temporal_signature.compute_velocity", lambda tile_id: SimpleNamespace(velocities=[0.1, 0.2, 0.4], trend="accelerating", acceleration=0.2, latest_velocity=0.4, series=[{"date_pair": {"before": "2020-01-01", "after": "2021-01-01"}, "velocity": 0.2, "source": "combined"}, {"date_pair": {"before": "2021-01-01", "after": "2023-01-01"}, "velocity": 0.4, "source": "combined"}]))
    monkeypatch.setattr("backend.main.public_url", lambda request, path: "/generated/test.png")
    monkeypatch.setattr("backend.main.tile_thumbnail", lambda *args, **kwargs: Path("/tmp/test.png"))

    response = client.get("/tiles/T9/temporal-evolution")
    assert response.status_code == 200
    payload = response.json()
    assert payload["tile_id"] == "T9"
    assert len(payload["frames"]) >= 2
    assert payload["frames"][0]["date"] == "2020-01-01"
    assert payload["frames"][0]["stage"]
