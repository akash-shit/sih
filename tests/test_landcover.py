from app.change.landcover import classify_land_cover, optical_weights


def test_landcover_boundaries_and_unknowns():
    assert classify_land_cover(None, None) == "urban_bare"
    assert classify_land_cover(0.56, 0) == "dense_vegetation"
    assert classify_land_cover(0.30, 0) == "sparse_vegetation"
    assert classify_land_cover(0, 0.11) == "water"
    assert optical_weights(None) == (0.65, 0.35)
