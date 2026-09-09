"""
Stage 9 -- Text Search
Stage 10 -- Image-to-Image Search

Both are the same operation underneath: embed a query into the shared
CLIP space, ask FAISS for nearest neighbours, resolve those ids back
to rich metadata in SQLite. The only difference is which embedder
function produces the query vector.
"""
from dataclasses import dataclass
from typing import Optional

from PIL import Image

from app.embeddings.clip_embedder import embed_text, embed_image_tile, embed_uploaded_image
from app.geospatial import catalog_db as db
from app.index.vector_index import VectorIndex


@dataclass
class SearchResult:
    vector_id: int
    tile_id: str
    acquisition_date: str
    sensor: str
    tile_path: str
    similarity: float
    bbox_wgs84: tuple
    ndvi_mean: float


def _rows_to_results(vector_ids: list[int], scores: list[float]) -> list[SearchResult]:
    rows = db.get_tiles_by_ids(vector_ids)
    by_id = {r["vector_id"]: r for r in rows}
    score_by_id = dict(zip(vector_ids, scores))
    out = []
    for vid in vector_ids:
        r = by_id.get(vid)
        if r is None:
            continue  # vector existed in FAISS but its tile row was later removed
        out.append(SearchResult(
            vector_id=vid, tile_id=r["tile_id"], acquisition_date=r["acquisition_date"],
            sensor=r["sensor"], tile_path=r["tile_path"], similarity=score_by_id[vid],
            bbox_wgs84=(r["minlon"], r["minlat"], r["maxlon"], r["maxlat"]),
            ndvi_mean=r["ndvi_mean"],
        ))
    return out


def _apply_filters(results: list[SearchResult], date_from: Optional[str], date_to: Optional[str],
                    sensor: Optional[str]) -> list[SearchResult]:
    def keep(r: SearchResult) -> bool:
        if date_from and r.acquisition_date < date_from:
            return False
        if date_to and r.acquisition_date > date_to:
            return False
        if sensor and r.sensor != sensor:
            return False
        return True
    return [r for r in results if keep(r)]


def text_search(query: str, top_k: int = 10, date_from: str = None, date_to: str = None,
                 sensor: str = None, aoi_id: int | None = None) -> list[SearchResult]:
    """Stage 9. Example: text_search('newly built structures near a river')"""
    query_vec = embed_text(query)
    index = VectorIndex()
    ids, scores = index.search(query_vec, top_k=min(top_k * 10, 500))
    results = _rows_to_results(ids, scores)
    if aoi_id is not None:
        valid_ids = set(db.get_vector_ids_for_aoi(int(aoi_id)))
        results = [r for r in results if r.vector_id in valid_ids]
    results = _apply_filters(results, date_from, date_to, sensor)
    return results[:top_k]


def image_search_by_tile(tile_path: str, top_k: int = 10, exclude_self: bool = True) -> list[SearchResult]:
    """Stage 10, variant A: analyst clicks an already-indexed tile and
    wants visually/semantically similar tiles."""
    query_vec = embed_image_tile(tile_path)
    index = VectorIndex()
    ids, scores = index.search(query_vec, top_k=top_k + 1)
    results = _rows_to_results(ids, scores)
    if exclude_self:
        results = [r for r in results if r.tile_path != tile_path]
    return results[:top_k]


def image_search_by_upload(pil_image: Image.Image, top_k: int = 10, aoi_id: int | None = None) -> list[SearchResult]:
    """Stage 10, variant B: analyst uploads an arbitrary example image
    (e.g. a reference photo of a type of structure) not already in the index."""
    query_vec = embed_uploaded_image(pil_image)
    index = VectorIndex()
    ids, scores = index.search(query_vec, top_k=min(top_k * 10, 500))
    results = _rows_to_results(ids, scores)
    if aoi_id is not None:
        valid_ids = set(db.get_vector_ids_for_aoi(int(aoi_id)))
        results = [r for r in results if r.vector_id in valid_ids]
    return results[:top_k]
