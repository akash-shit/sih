from app.change.priority import compute_priority, haversine_km


def test_priority_tier_and_hotspot_decay():
    candidate = {"lat": 0, "lon": 0, "candidate_id": 1}
    aoi = {"priority_tier": "high"}
    score, reasons = compute_priority(candidate, aoi, [{"lat": 0, "lon": 0, "candidate_id": 9}])
    assert score == 0.9
    assert "aoi_tier" in reasons
    assert any(reason.startswith("near_confirmed_hotspot:9:") for reason in reasons)
    assert haversine_km((0, 0), (0, 1)) > 100
