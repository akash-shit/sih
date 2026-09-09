"""
Stage 17 -- Analyst Review, Audit Trail, and Feedback Reranking

Everything the review UI needs is assembled here so the (future)
FastAPI /review endpoints and the eventual React/Streamlit screen stay
thin. The reranking rule is intentionally simple and explainable for a
prototype: a confirmed candidate's embedding nudges the ranking of
still-open candidates in the SAME cluster upward, since a confirmed
real change is evidence about what "real change" looks like in that
neighbourhood of the embedding space -- not a black-box retrain.
"""
from dataclasses import dataclass

import numpy as np

from app.geospatial import catalog_db as db
from app.index.vector_index import VectorIndex


@dataclass
class ReviewItem:
    candidate_id: int
    tile_id: str
    date_before: str
    date_after: str
    combined_score: float
    embedding_drift: float
    spectral_delta: float
    change_type: str | None
    change_type_confidence: float | None
    tile_path_before: str
    tile_path_after: str


def get_review_queue(limit: int = 50) -> list[ReviewItem]:
    rows = db.list_review_queue(include_suppressed=False, limit=limit)
    items = []
    for r in rows:
        before = db.get_tile(r["vector_id_before"])
        after = db.get_tile(r["vector_id_after"])
        items.append(ReviewItem(
            candidate_id=r["candidate_id"], tile_id=r["tile_id"],
            date_before=r["date_before"], date_after=r["date_after"],
            combined_score=r["combined_score"], embedding_drift=r["embedding_drift"],
            spectral_delta=r["spectral_delta"], change_type=r["change_type"],
            change_type_confidence=r["change_type_confidence"],
            tile_path_before=before["tile_path"] if before else "",
            tile_path_after=after["tile_path"] if after else "",
        ))
    return items


def submit_decision(candidate_id: int, decision: str, reason: str = None):
    """Analyst confirms or rejects. Always logged to audit_log
    regardless of outcome -- both are provenance, not just confirmations."""
    db.record_decision(candidate_id, decision, reason)
    if decision == "confirm":
        _boost_similar_open_candidates(candidate_id)
    elif decision == "reject":
        _suppress_similar_open_candidates(candidate_id)


def _boost_similar_open_candidates(confirmed_candidate_id: int, boost: float = 0.05,
                                    similarity_threshold: float = 0.85):
    """Human-in-the-loop reranking: find open (undecided) candidates
    whose 'after' embedding is close to the confirmed one's, and give
    them a modest score boost so they surface higher next time the
    queue is rendered -- without ever auto-confirming anything."""
    with db.get_conn() as conn:
        confirmed = conn.execute(
            "SELECT * FROM change_candidates WHERE candidate_id = ?", (confirmed_candidate_id,)
        ).fetchone()
        if confirmed is None:
            return

        decided_ids = {
            row["candidate_id"] for row in
            conn.execute("SELECT DISTINCT candidate_id FROM audit_log").fetchall()
        }
        open_candidates = conn.execute(
            "SELECT * FROM change_candidates WHERE suppressed = 0"
        ).fetchall()

    index = VectorIndex()
    confirmed_vec = index.get_vector(confirmed["vector_id_after"])

    for cand in open_candidates:
        if cand["candidate_id"] in decided_ids or cand["candidate_id"] == confirmed_candidate_id:
            continue
        cand_vec = index.get_vector(cand["vector_id_after"])
        sim = float(np.dot(confirmed_vec, cand_vec))  # both pre-normalized
        if sim >= similarity_threshold:
            new_score = min(cand["combined_score"] + boost, 1.0)
            with db.get_conn() as conn:
                conn.execute(
                    "UPDATE change_candidates SET combined_score = ? WHERE candidate_id = ?",
                    (new_score, cand["candidate_id"]),
                )


def _suppress_similar_open_candidates(rejected_candidate_id: int, similarity_threshold: float = 0.92):
    """Suppress only unresolved candidates whose after-tile embedding is
    genuinely similar to a rejected candidate, without deleting evidence."""
    with db.get_conn() as conn:
        rejected = conn.execute(
            "SELECT * FROM change_candidates WHERE candidate_id = ?", (rejected_candidate_id,)
        ).fetchone()
        if rejected is None:
            return
        decided_ids = {row["candidate_id"] for row in conn.execute("SELECT DISTINCT candidate_id FROM audit_log")}
        open_candidates = conn.execute("SELECT * FROM change_candidates WHERE suppressed=0").fetchall()

    index = VectorIndex()
    rejected_vec = index.get_vector(rejected["vector_id_after"])
    for candidate in open_candidates:
        if candidate["candidate_id"] in decided_ids or candidate["candidate_id"] == rejected_candidate_id:
            continue
        candidate_vec = index.get_vector(candidate["vector_id_after"])
        similarity = float(np.dot(rejected_vec, candidate_vec))
        if similarity >= similarity_threshold:
            with db.get_conn() as conn:
                conn.execute(
                    "UPDATE change_candidates SET suppressed=1, suppression_reason=? WHERE candidate_id=?",
                    (f"similar_to_rejected_candidate_{rejected_candidate_id}_similarity={similarity:.3f}", candidate["candidate_id"]),
                )
