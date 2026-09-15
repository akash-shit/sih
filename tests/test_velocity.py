from datetime import datetime
from types import SimpleNamespace

from app.change.temporal_signature import _effective_score, compute_velocity


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
