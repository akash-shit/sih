import numpy as np

from app.discovery.clustering import _choose_cluster_strategy


def test_discovery_uses_partition_strategy_when_hdbscan_is_too_sparse():
    strategy = _choose_cluster_strategy(120, min_cluster_size=3)
    assert strategy["method"] in {"hdbscan", "partition"}

    partition = _choose_cluster_strategy(18, min_cluster_size=3)
    assert partition["method"] == "partition"
    assert partition["k"] >= 10


def test_discovery_partition_target_is_in_10_12_range():
    config = _choose_cluster_strategy(150, min_cluster_size=3)
    if config["method"] == "partition":
        assert 10 <= config["k"] <= 12
