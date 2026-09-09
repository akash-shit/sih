"""
The ingestion orchestrator. This is the one function every other entry
point (CLI script today, a FastAPI /ingest endpoint later) calls.

Flow (mirrors Stages 2-8 + 18 from the architecture doc):
    scene -> inspect -> tile (+MGRS id) -> per-tile NDVI/NDWI/quality
    -> SQLite insert (get vector_id) -> CLIP embed -> FAISS add_with_ids
    -> save index

Re-running this on a scene that is already registered is a safe no-op
(idempotent ingestion), and running it on a brand-new scene only adds
to the existing FAISS index -- it never rebuilds it. That combination
is what satisfies the "incremental ingestion, no full rebuild"
requirement end to end, not just at the FAISS layer.
"""
import logging

from app.geospatial import catalog_db as db
from app.geospatial.reader import inspect_scene
from app.geospatial.rendering import has_valid_multispectral_data
from app.geospatial.tiler import tile_scene
from app.geospatial.features import compute_tile_features
from app.embeddings.clip_embedder import embed_image_tiles_batch
from app.index.vector_index import VectorIndex

log = logging.getLogger("ingest")


def ingest_scene(scene_path: str, acquisition_date: str, sensor: str, aoi_id: int = None,
                  acquisition_date_source: str = None, cloud_cover_percent: float = None,
                  source_metadata: dict = None) -> dict:
    """aoi_id and the metadata_* kwargs are optional so this still works
    exactly as before for ad-hoc single-scene ingestion (e.g. from the
    CLI without an AOI concept); app/pipeline/onboard_aoi.py always
    passes all of them when onboarding a real, metadata-rich batch."""
    db.init_db()

    if db.scene_already_ingested(scene_path):
        log.info("Scene already ingested, skipping: %s", scene_path)
        return {"scene_path": scene_path, "status": "skipped_duplicate", "tiles_added": 0}

    # Stage 2: sanity-check the file opens and has a real CRS before we
    # spend time tiling it.
    info = inspect_scene(scene_path)
    if info.crs == "UNKNOWN":
        raise ValueError(f"Scene has no CRS, cannot georeference: {scene_path}")
    if not has_valid_multispectral_data(scene_path):
        raise ValueError(f"Scene has no valid nonzero B02/B03/B04/B08 pixels: {scene_path}")

    # Register the parent scene first -- tiles carry a foreign key to it.
    db.register_scene(
        scene_path, acquisition_date, sensor, aoi_id=aoi_id,
        acquisition_date_source=acquisition_date_source,
        cloud_cover_percent=cloud_cover_percent, source_metadata=source_metadata,
    )

    # Stage 3/4: tile into the fixed MGRS grid.
    tiles = tile_scene(scene_path, acquisition_date, sensor)
    log.info("Tiled %s into %d tiles", scene_path, len(tiles))

    # Stage 5 + 6: compute spectral features and register in SQLite,
    # capturing the vector_id we'll reuse as the FAISS id.
    vector_ids, tile_paths = [], []
    for tile in tiles:
        features = compute_tile_features(tile.tile_path)
        vector_id = db.insert_tile(tile, features, aoi_id=aoi_id)
        vector_ids.append(vector_id)
        tile_paths.append(tile.tile_path)

    # Stage 7 + 8 + 18: embed in one batch, then append (not rebuild) the index.
    vectors = embed_image_tiles_batch(tile_paths)
    index = VectorIndex()
    index.add_vectors(vectors, vector_ids)
    index.save()

    if aoi_id is not None:
        db.update_aoi_extent(aoi_id)

    log.info("Indexed %d vectors (FAISS ntotal now %d)", len(vector_ids), index.ntotal)
    return {"scene_path": scene_path, "status": "ingested", "tiles_added": len(vector_ids)}
