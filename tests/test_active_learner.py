import pickle

from sklearn.linear_model import LogisticRegression

from app.review import queue


def test_active_learner_uses_trained_model(monkeypatch, tmp_path):
    model_path = tmp_path / "active_learner.pkl"
    model = LogisticRegression(random_state=0, max_iter=1000)
    model.fit([[0.1, 0.2, 0.0, 0.0, 0.4, 0.0], [0.9, 0.8, 0.0, 0.0, 0.8, 1.0]], [0, 1])
    model_path.write_bytes(pickle.dumps(model))

    rows = [
        {"candidate_id": 1, "vector_id_before": "v-before-1", "vector_id_after": "v-after-1", "combined_score": 0.1, "embedding_drift": 0.1, "spectral_delta": 0.2, "cloud_fraction": 0.0, "haze_score": 0.0, "fused_score": 0.4, "sar_score": 0.0, "date_before": "2024-01-01", "date_after": "2024-01-15", "tile_id": "tile-1", "change_type": None, "change_type_confidence": None},
        {"candidate_id": 2, "vector_id_before": "v-before-2", "vector_id_after": "v-after-2", "combined_score": 0.9, "embedding_drift": 0.9, "spectral_delta": 0.8, "cloud_fraction": 0.0, "haze_score": 0.0, "fused_score": 0.8, "sar_score": 1.0, "date_before": "2024-01-01", "date_after": "2024-01-15", "tile_id": "tile-2", "change_type": None, "change_type_confidence": None},
    ]

    monkeypatch.setattr(queue, "LEARNER_PATH", model_path)
    monkeypatch.setattr(queue.db, "list_review_queue", lambda include_suppressed=False, limit=50: rows)
    monkeypatch.setattr(queue.db, "get_tile", lambda vector_id: {"tile_path": f"/tmp/{vector_id}.tif"})

    ranked = queue.get_review_queue(limit=10, sort="learned")

    assert {item.candidate_id for item in ranked} == {1, 2}
    assert all(item.predicted_confirm_prob is not None for item in ranked)
    assert ranked[0].candidate_id == 2
