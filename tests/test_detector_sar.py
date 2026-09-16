from app.geospatial.sar_features import SarFeatures, sar_change_score


def test_sar_score_is_independent_of_optical_when_valid():
    before = SarFeatures(-12, -18, 1, 1, 6, 1)
    after = SarFeatures(-8, -14, 1, 1, 6, 1)
    assert 0 < sar_change_score(before, after) <= 1
