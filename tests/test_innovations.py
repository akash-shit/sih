import numpy as np

from app.change.adaptive import adaptive_score, infer_land_cover, strategic_priority, active_learning_probability
from app.change.heatmap import explainable_heatmaps
from app.change.sar import fuse_modalities, sar_change_score


def test_sar_fusion_is_bounded_and_detects_delta():
    score = sar_change_score(np.ones((4, 4)), np.ones((4, 4)) * 4,
                             np.ones((4, 4)), np.ones((4, 4)) * 3)
    assert 0 < score <= 1
    assert 0 <= fuse_modalities(.4, score) <= 1


def test_adaptive_land_cover_and_priority():
    assert infer_land_cover(.7, 0) == "dense_vegetation"
    assert adaptive_score(.5, .1, land_cover="water") != adaptive_score(.5, .1, land_cover="urban")
    priority = strategic_priority(.9, criticality=.9, population_exposure=.8)
    assert priority.score > .7 and "critical_area" in priority.reasons
    assert .0 <= active_learning_probability(.5, uncertainty=1) <= 1


def test_heatmaps_are_explainable_data_urls():
    maps = explainable_heatmaps(np.zeros((3, 3)), np.eye(3))
    assert maps["spectral"].startswith("data:image/png;base64,")
