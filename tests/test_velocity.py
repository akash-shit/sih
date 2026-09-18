from datetime import datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.change.temporal_signature import _effective_score, compute_velocity, temporal_profile
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
