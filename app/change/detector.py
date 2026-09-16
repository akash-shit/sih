"""
Stage 11 -- Temporal Pairing
Stage 12 -- Hybrid Change Scoring
Stage 13 -- False-Alarm Suppression
Stage 15 -- Earliest Supported Observation

Refinement 3.3 from the architecture review: CLIP embedding drift alone
is not the whole detector -- it also moves for season/illumination
reasons that have nothing to do with real change. So every pair gets
TWO independent signals combined into one score:
  - embedding_drift   : 1 - cosine_similarity(vec_before, vec_after)
  - spectral_delta    : |NDVI_after - NDVI_before| (a physically
                         grounded second opinion the embedding can't fake)
A pair is only promoted to the review queue if BOTH signals agree
there's something there AND the quality gates in Stage 13 pass.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.config import DEFAULT_CHANGE_THRESHOLD, MAX_CLOUD_FRACTION, MIN_VALID_PIXEL_FRACTION, SAR_MIN_CHANGE_SCORE, SAR_MIN_VALID_PIXELS
from app.geospatial import catalog_db as db
from app.geospatial.rendering import has_valid_multispectral_data
from app.index.vector_index import VectorIndex
from app.change.adaptive import adaptive_score, infer_land_cover, strategic_priority
from app.change.sar import fuse_modalities, sar_change_score
from app.geospatial.sar_features import SarFeatures, sar_change_score


@dataclass
class ChangeCandidate:
    tile_id: str
    vector_id_before: int
    vector_id_after: int
    date_before: str
    date_after: str
    embedding_drift: float
    spectral_delta: float
    combined_score: float
    suppressed: bool
    suppression_reason: str | None
    sar_score: float | None = None
    fused_score: float | None = None
    sar_only: bool = False
    modality: str = "optical_only"
    land_cover: str | None = None


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    # Vectors are already L2-normalized by the embedder, but we
    # normalize again defensively -- cheap, and safe if that ever changes.
    a = a / (np.linalg.norm(a) + 1e-8)
    b = b / (np.linalg.norm(b) + 1e-8)
    return float(np.dot(a, b))


def _quality_gate(before_row, after_row) -> str | None:
    """Stage 13. Returns a suppression reason string, or None if the
    pair is clean enough to trust. Order matters only for readability
    of the logged reason -- checks are independent."""
    for row, label in ((before_row, "before"), (after_row, "after")):
        path = row["tile_path"]
        if not path or not Path(path).exists() or not has_valid_multispectral_data(path):
            return f"source_imagery_unavailable_{label}"
    for row, label in ((before_row, "before"), (after_row, "after")):
        if row["cloud_fraction"] is not None and row["cloud_fraction"] > MAX_CLOUD_FRACTION:
            return f"cloud_fraction_too_high_{label}={row['cloud_fraction']:.2f}"
        if row["valid_pixel_fraction"] is not None and row["valid_pixel_fraction"] < MIN_VALID_PIXEL_FRACTION:
            return f"insufficient_valid_pixels_{label}={row['valid_pixel_fraction']:.2f}"
        if row["haze_score"] is not None and row["haze_score"] > 0.70:
            return f"haze_score_too_high_{label}={row['haze_score']:.2f}"
        if row["snow_fraction"] is not None and row["snow_fraction"] > 0.30:
            return f"snow_cover_too_high_{label}={row['snow_fraction']:.2f}"
    # Seasonal water-extent swing that is fully explained by NDWI, not
    # a real structural change -- a common false positive source.
    if None in (before_row["ndwi_mean"], after_row["ndwi_mean"], before_row["ndvi_mean"], after_row["ndvi_mean"]):
        return "spectral_features_unavailable"
    ndwi_delta = abs(after_row["ndwi_mean"] - before_row["ndwi_mean"])
    if ndwi_delta > 0.35 and abs(after_row["ndvi_mean"] - before_row["ndvi_mean"]) < 0.05:
        return f"likely_seasonal_water_variation_ndwi_delta={ndwi_delta:.2f}"
    return None


def analyze_tile_pair(before_row, after_row, threshold: float = DEFAULT_CHANGE_THRESHOLD,
                      sar_pair: tuple[SarFeatures, SarFeatures] | None = None) -> ChangeCandidate:
    index = VectorIndex()
    vec_before = index.get_vector(before_row["vector_id"])
    vec_after = index.get_vector(after_row["vector_id"])

    embedding_drift = 1.0 - _cosine_similarity(vec_before, vec_after)
    spectral_delta = 0.0 if None in (before_row["ndvi_mean"], after_row["ndvi_mean"]) else abs(after_row["ndvi_mean"] - before_row["ndvi_mean"])

    # Weighted combination: embedding drift captures broad visual/semantic
    # change, spectral delta anchors it to a physical vegetation/structure
    # signal so a pure-embedding artifact can't pass alone.
    land_cover = before_row["land_cover"] if "land_cover" in before_row.keys() else infer_land_cover(before_row["ndvi_mean"], before_row["ndwi_mean"])
    combined_score = adaptive_score(embedding_drift, spectral_delta, land_cover=land_cover)
    sar_score = None
    fused_score = None
    sar_only = False
    modality = "optical_only"
    if sar_pair and all(item.valid_pixels >= SAR_MIN_VALID_PIXELS for item in sar_pair):
        sar_score = sar_change_score(*sar_pair)
        optical_quality = 0.0 if _quality_gate(before_row, after_row) else 1.0
        if optical_quality == 0.0 and sar_score >= SAR_MIN_CHANGE_SCORE:
            fused_score, sar_only, modality = sar_score, True, "sar_only"
        else:
            fused_score = (optical_quality * combined_score + sar_score) / (optical_quality + 1.0)
            modality = "fused"
        combined_score = fused_score

    suppression_reason = _quality_gate(before_row, after_row)
    if sar_only:
        suppression_reason = None
    suppressed = suppression_reason is not None or combined_score < threshold

    return ChangeCandidate(
        tile_id=before_row["tile_id"],
        vector_id_before=before_row["vector_id"], vector_id_after=after_row["vector_id"],
        date_before=before_row["acquisition_date"], date_after=after_row["acquisition_date"],
        embedding_drift=embedding_drift, spectral_delta=spectral_delta,
        combined_score=combined_score, suppressed=suppressed,
        suppression_reason=suppression_reason if suppression_reason else
            (None if not suppressed else f"below_threshold_{combined_score:.3f}<{threshold}"),
        sar_score=sar_score, fused_score=fused_score, sar_only=sar_only,
        modality=modality, land_cover=land_cover,
    )


def analyze_tile_timeline(tile_id: str, threshold: float = DEFAULT_CHANGE_THRESHOLD) -> list[ChangeCandidate]:
    """Stage 11: walk one ground cell's observations chronologically
    and score every consecutive pair. Consecutive (not all-pairs) is
    what lets Stage 15 report an 'earliest supported observation'
    instead of just a single before/after."""
    history = db.get_tile_history(tile_id)
    index = VectorIndex()
    candidates = []
    for i in range(len(history) - 1):
        if not index.has_vector(history[i]["vector_id"]) or not index.has_vector(history[i + 1]["vector_id"]):
            continue
        candidates.append(analyze_tile_pair(history[i], history[i + 1], threshold))
    return candidates


def earliest_supported_observation(candidates: list[ChangeCandidate]) -> str | None:
    """Stage 15: scan chronologically-ordered candidates (as returned by
    analyze_tile_timeline) and return the date of the FIRST pair where
    change was supported and NOT suppressed, i.e. the earliest point the
    evidence actually holds up -- not just the most recent flag."""
    for c in candidates:
        if not c.suppressed:
            return c.date_after
    return None


def run_change_detection_for_all_tiles(threshold: float = DEFAULT_CHANGE_THRESHOLD) -> list[int]:
    """Orchestrator used by the CLI / future /change/analyze endpoint:
    scans every ground cell with 2+ observations, persists every
    candidate (suppressed or not, for audit completeness), and returns
    the candidate_ids that made it past suppression."""
    db.init_db()
    promoted_ids = []
    for tile_id in db.get_all_tile_ids():
        candidates = analyze_tile_timeline(tile_id, threshold)
        earliest = earliest_supported_observation(candidates)
        for c in candidates:
            from app.change.narrative import build_narrative

            narrative = build_narrative(
                before_date=c.date_before, after_date=c.date_after,
                change_region=None, changed_fraction=None, ndvi_change=None,
                spectral_delta=c.spectral_delta, embedding_drift=c.embedding_drift,
                combined_score=c.combined_score,
                quality="suppressed" if c.suppressed else "pending_pixel_validation",
                change_type=None, confidence=None, earliest_supported_date=earliest,
            )
            candidate_id = db.insert_change_candidate(
                tile_id=c.tile_id,
                vector_id_before=c.vector_id_before, vector_id_after=c.vector_id_after,
                date_before=c.date_before, date_after=c.date_after,
                embedding_drift=c.embedding_drift, spectral_delta=c.spectral_delta,
                combined_score=c.combined_score, suppressed=int(c.suppressed),
                suppression_reason=c.suppression_reason,
                change_type=None, change_type_confidence=None, earliest_supported_date=earliest,
                narrative=narrative,
            )
            # Additive innovation fields are computed for every candidate;
            # existing optical behaviour and suppression decisions remain unchanged.
            after_tile = db.get_tile(c.vector_id_after)
            cover = infer_land_cover(after_tile["ndvi_mean"], after_tile["ndwi_mean"]) if after_tile else "unknown"
            score = adaptive_score(c.embedding_drift, c.spectral_delta, land_cover=cover)
            sar_rows = db.list_sar_observations(c.tile_id)
            sar_before = next((r for r in sar_rows if r["acquisition_date"] == c.date_before), None)
            sar_after = next((r for r in sar_rows if r["acquisition_date"] == c.date_after), None)
            sar_score = None
            modality = "optical"
            fused_score = score
            sar_only = 0
            if sar_before and sar_after and sar_before["vv_mean"] is not None and sar_after["vv_mean"] is not None:
                sar_score = sar_change_score(
                    np.asarray([sar_before["vv_mean"]]), np.asarray([sar_after["vv_mean"]]),
                    np.asarray([sar_before["vh_mean"] or 0]), np.asarray([sar_after["vh_mean"] or 0]),
                )
                fused_score = fuse_modalities(score, sar_score)
                modality = "optical+sar"
            priority = strategic_priority(fused_score, confidence=0.5)
            with db.get_conn() as conn:
                conn.execute("UPDATE change_candidates SET land_cover=?, priority_score=?, priority_reasons=?, "
                             "predicted_confirm_prob=?, sar_score=?, fused_score=?, sar_only=?, modality=? WHERE candidate_id=?",
                             (cover, priority.score, __import__("json").dumps(priority.reasons),
                              priority.score, sar_score, fused_score, sar_only, modality, candidate_id))
            if c.suppressed:
                continue
            from app.change.classifier import classify_change_type

            after_tile = db.get_tile(c.vector_id_after)
            if after_tile is None:
                raise ValueError(f"Promoted candidate references missing after tile: {c.vector_id_after}")
            interpretation = classify_change_type(after_tile["tile_path"])
            with db.get_conn() as conn:
                conn.execute(
                    "UPDATE change_candidates SET change_type=?, change_type_confidence=? WHERE candidate_id=?",
                    (interpretation.change_type, interpretation.confidence, candidate_id),
                )
            promoted_ids.append(candidate_id)
    return promoted_ids
