"""Controlled real-tile migration from the legacy index to RemoteCLIP."""
import json
import os
from pathlib import Path

import faiss
import numpy as np

from app.config import EMBEDDING_DIM, REMOTECLIP_CHECKPOINT
from app.embeddings.clip_embedder import embed_image_tile
from app.geospatial import catalog_db as db
from app.geospatial.rendering import has_valid_multispectral_data


INDEX_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "index" / "tiles.faiss"
TEMP_INDEX_PATH = INDEX_PATH.with_suffix(".remoteclip.tmp.faiss")
REPORT_PATH = INDEX_PATH.parent / "remoteclip_migration_report.json"


def _load_tiles() -> list[dict]:
    with db.get_conn() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT vector_id, tile_id, tile_path, scene_path, acquisition_date, aoi_id "
            "FROM tiles ORDER BY vector_id"
        ).fetchall()]


def migrate() -> dict:
    if not REMOTECLIP_CHECKPOINT.is_file():
        raise RuntimeError(f"RemoteCLIP checkpoint not found: {REMOTECLIP_CHECKPOINT}")

    tiles = _load_tiles()
    eligible = []
    skipped = []
    for tile in tiles:
        path = Path(tile["tile_path"])
        if not path.is_file():
            skipped.append({"vector_id": tile["vector_id"], "tile_path": tile["tile_path"], "reason": "missing_tile_file"})
        elif not has_valid_multispectral_data(path):
            skipped.append({"vector_id": tile["vector_id"], "tile_path": tile["tile_path"], "reason": "invalid_multispectral_source"})
        else:
            eligible.append(tile)

    vectors = []
    successes = []
    failures = list(skipped)
    for tile in eligible:
        try:
            vector = embed_image_tile(tile["tile_path"])
            if vector.shape != (EMBEDDING_DIM,):
                raise ValueError(f"unexpected dimension {vector.shape}")
            if not np.isfinite(vector).all():
                raise ValueError("embedding contains non-finite values")
            if not np.isclose(np.linalg.norm(vector), 1.0, atol=1e-4):
                raise ValueError("embedding is not L2-normalized")
            vectors.append(vector)
            successes.append(tile)
        except Exception as exc:
            failures.append({"vector_id": tile["vector_id"], "tile_path": tile["tile_path"], "reason": str(exc)})

    if not vectors:
        raise RuntimeError("No eligible real tiles produced a RemoteCLIP embedding.")

    vector_array = np.asarray(vectors, dtype=np.float32)
    new_index = faiss.IndexIDMap2(faiss.IndexFlatIP(EMBEDDING_DIM))
    ids = np.asarray([tile["vector_id"] for tile in successes], dtype=np.int64)
    new_index.add_with_ids(vector_array, ids)

    indexed_ids = set(int(value) for value in faiss.vector_to_array(new_index.id_map))
    success_ids = set(int(value) for value in ids)
    sqlite_ids = {int(tile["vector_id"]) for tile in tiles}
    if indexed_ids != success_ids or len(indexed_ids) != len(successes):
        raise RuntimeError("Temporary index IDs are not unique or do not match successful embeddings.")
    if not indexed_ids <= sqlite_ids:
        raise RuntimeError("Temporary index contains an orphan vector ID.")
    if new_index.d != EMBEDDING_DIM:
        raise RuntimeError(f"Temporary index dimension mismatch: {new_index.d}")
    if new_index.ntotal != len(successes):
        raise RuntimeError("Temporary index count does not match successful embeddings.")

    faiss.write_index(new_index, str(TEMP_INDEX_PATH))
    report = {
        "checkpoint": str(REMOTECLIP_CHECKPOINT),
        "model": "RemoteCLIP-ViT-B-32",
        "architecture": "ViT-B-32",
        "embedding_dimension": EMBEDDING_DIM,
        "index_type": type(new_index).__name__,
        "sqlite_tile_count": len(tiles),
        "eligible_tile_count": len(eligible),
        "successful_embedding_count": len(successes),
        "failed_or_skipped_count": len(failures),
        "failed_or_skipped": failures,
        "temporary_index": str(TEMP_INDEX_PATH),
        "production_index_replaced": False,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def replace_validated_index() -> dict:
    if not TEMP_INDEX_PATH.is_file():
        raise RuntimeError(f"Validated temporary index not found: {TEMP_INDEX_PATH}")
    validated = faiss.read_index(str(TEMP_INDEX_PATH))
    if not isinstance(validated, faiss.IndexIDMap2) or validated.d != EMBEDDING_DIM:
        raise RuntimeError("Temporary index failed final type/dimension validation.")
    replacement = INDEX_PATH.with_suffix(".remoteclip.new.faiss")
    os.replace(TEMP_INDEX_PATH, replacement)
    os.replace(replacement, INDEX_PATH)
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    report["production_index_replaced"] = True
    report["new_vector_count"] = validated.ntotal
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
