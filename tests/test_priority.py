from app.change.priority import compute_priority, haversine_km


def test_priority_tier_and_hotspot_decay():
    candidate = {"lat": 0, "lon": 0, "candidate_id": 1}
    aoi = {"priority_tier": "high"}
    score = compute_priority(candidate, aoi, [{"lat": 0, "lon": 0, "candidate_id": 9}])
    assert score == 0.9
    assert haversine_km((0, 0), (0, 1)) > 100
