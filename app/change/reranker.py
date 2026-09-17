"""Legacy active-learning reranker.

The review queue now owns ranking and this module is not imported by the
production API.  It remains as a compatibility helper for offline callers;
new code should use ``app.review.queue.get_review_queue(sort="learned")``.
"""
from .adaptive import active_learning_probability

def rerank_candidates(candidates: list[dict]) -> list[dict]:
    """Return a stable ranking without mutating caller-owned dictionaries."""
    ranked = []
    for candidate in candidates:
        item = dict(candidate)
        item["predicted_confirm_prob"] = active_learning_probability(
            item.get("combined_score", 0) or 0,
            uncertainty=item.get("uncertainty"),
            diversity=item.get("diversity", 0) or 0,
        )
        ranked.append(item)
    return sorted(ranked, key=lambda x: (x["predicted_confirm_prob"], x.get("priority_score", 0) or 0), reverse=True)

__all__ = ["rerank_candidates", "active_learning_probability"]
