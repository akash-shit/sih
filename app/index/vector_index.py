"""
Stage 8 -- FAISS Indexing
Stage 18 -- Incremental Ingestion (add_vectors appends, never rebuilds)

We use IndexIDMap2 around a flat inner-product index. Two design
choices matter for this PS specifically:

1. IndexIDMap2 lets us use OUR OWN ids (the SQLite `vector_id`
   primary key) as FAISS ids, instead of FAISS's own sequential
   position. That is what makes SQLite <-> FAISS lookups trivial and
   is required for `remove_ids` to work at all.
2. IndexFlatIP (inner product) on L2-normalized vectors is
   mathematically equivalent to cosine similarity, which is the
   standard similarity for CLIP-style embeddings. Flat is exact
   (no approximation) which is fine at prototype scale (tens of
   thousands of tiles); if you outgrow that, swap to
   IndexIVFFlat/HNSW behind this same interface without touching
   any calling code.
"""
from pathlib import Path

import faiss
import numpy as np

from app.config import INDEX_DIR, EMBEDDING_DIM

INDEX_PATH = INDEX_DIR / "tiles.faiss"


class VectorIndex:
    def __init__(self, dim: int = EMBEDDING_DIM, path: Path = INDEX_PATH):
        self.dim = dim
        self.path = path
        if path.exists():
            self.index = faiss.read_index(str(path))
        else:
            base = faiss.IndexFlatIP(dim)
            self.index = faiss.IndexIDMap2(base)

    def add_vectors(self, vectors: np.ndarray, ids: list[int]):
        """Append new vectors without touching anything already
        indexed -- this IS the incremental-ingestion requirement
        (2.2.6 / Stage 18): a new scene never triggers a full rebuild."""
        assert vectors.shape[0] == len(ids)
        ids_arr = np.array(ids, dtype=np.int64)
        self.index.add_with_ids(vectors.astype(np.float32), ids_arr)

    def search(self, query_vector: np.ndarray, top_k: int = 10) -> tuple[list[int], list[float]]:
        q = query_vector.astype(np.float32).reshape(1, -1)
        scores, ids = self.index.search(q, top_k)
        ids, scores = ids[0], scores[0]
        keep = ids != -1  # FAISS pads with -1 if fewer than top_k exist
        return ids[keep].tolist(), scores[keep].tolist()

    def get_vector(self, vector_id: int) -> np.ndarray:
        return self.index.reconstruct(int(vector_id))

    def has_vector(self, vector_id: int) -> bool:
        try:
            self.get_vector(vector_id)
        except RuntimeError:
            return False
        return True

    def remove(self, ids: list[int]):
        self.index.remove_ids(np.array(ids, dtype=np.int64))

    def save(self):
        faiss.write_index(self.index, str(self.path))

    @property
    def ntotal(self) -> int:
        return self.index.ntotal
