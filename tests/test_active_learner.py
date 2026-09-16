from app.change.reranker import rerank_candidates


def test_active_learner_reranking_keeps_all_candidates():
    result = rerank_candidates([{"candidate_id": 1, "combined_score": 0.1}, {"candidate_id": 2, "combined_score": 0.9}])
    assert {row["candidate_id"] for row in result} == {1, 2}
    assert all(0 <= row["predicted_confirm_prob"] <= 1 for row in result)
