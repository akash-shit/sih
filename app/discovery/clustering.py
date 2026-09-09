"""
Stage 16 -- Clustering / Discovery

Groups every embedded tile into clusters of visually/semantically
similar sites using HDBSCAN (density-based, so it does not force every
tile into a cluster and does not require picking k in advance -- both
matter for open-world satellite imagery where "how many types of site
exist in this AOI" isn't known ahead of time). Falls back to KMeans if
there are too few tiles for HDBSCAN's minimum cluster size, which
happens on small demo AOIs like the synthetic one used for testing.

This directly implements 2.2.4: "an analyst who identifies one location
of interest can discover other locations with comparable visual or
semantic characteristics without manually constructing a new query."
Once cluster_id is written to SQLite, "similar sites" is just
`SELECT ... WHERE cluster_id = ?` -- no new embedding call needed.
"""
import numpy as np
import hdbscan
from sklearn.cluster import KMeans

from app.geospatial import catalog_db as db
from app.geospatial.rendering import has_valid_multispectral_data
from app.index.vector_index import VectorIndex


def cluster_all_tiles(min_cluster_size: int = 3, fallback_k: int = 3) -> dict[int, int]:
    """Returns {vector_id: cluster_id}. cluster_id == -1 means HDBSCAN
    treated it as noise (a genuinely unusual tile) -- surfaced as-is
    rather than forced into a false grouping."""
    with db.get_conn() as conn:
        rows = conn.execute("SELECT vector_id, tile_path FROM tiles ORDER BY vector_id").fetchall()
    all_vector_ids = [row["vector_id"] for row in rows if has_valid_multispectral_data(row["tile_path"])]

    db.clear_tile_clusters()

    if len(all_vector_ids) < 2:
        return {}

    index = VectorIndex()
    vectors = np.stack([index.get_vector(vid) for vid in all_vector_ids])

    if len(all_vector_ids) >= min_cluster_size * 2:
        clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric="euclidean")
        labels = clusterer.fit_predict(vectors)
    else:
        # Small demo AOIs won't have enough tiles for HDBSCAN's density
        # requirement -- KMeans with a small k keeps discovery testable
        # at prototype scale without changing the downstream interface.
        k = min(fallback_k, len(all_vector_ids))
        labels = KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(vectors)

    assignment = {vid: int(label) for vid, label in zip(all_vector_ids, labels)}
    for vid, cluster_id in assignment.items():
        db.set_tile_cluster(vid, cluster_id)
    return assignment


def similar_sites_in_cluster(vector_id: int, limit: int = 20):
    """Stage 16's actual analyst-facing action: click one tile, get
    every other tile in its cluster, no new query."""
    row = db.get_tile(vector_id)
    if row is None or row["cluster_id"] is None or row["cluster_id"] == -1:
        # -1 is HDBSCAN's explicit "noise / does not belong to any
        # group" label -- returning other noise-labelled tiles here
        # would misrepresent them as similar when they are not.
        return []
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tiles WHERE cluster_id = ? AND vector_id != ? LIMIT ?",
            (row["cluster_id"], vector_id, limit),
        ).fetchall()
    return rows


def get_tiles_in_cluster(cluster_id: int):
    """Return every tile assigned to a cluster, excluding HDBSCAN noise."""
    if cluster_id == -1:
        return []
    with db.get_conn() as conn:
        return conn.execute(
            "SELECT * FROM tiles WHERE cluster_id = ? ORDER BY acquisition_date, vector_id",
            (cluster_id,),
        ).fetchall()
