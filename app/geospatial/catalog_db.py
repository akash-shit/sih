"""
Stage 6 -- Metadata and Provenance Storage
Stage 17 -- Analyst Review (the audit_log table)
Stage 18 -- Incremental Ingestion support (scenes.ingested flag)

SQLite is the "what and where" store. FAISS (app/index/vector_index.py)
is the "what's nearest" store. They are linked by a single shared
integer: vector_id. This file owns the schema and every read/write
against it, so no other module ever writes raw SQL.
"""
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS aois (
    aoi_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    source_folder TEXT,
    minlon REAL, minlat REAL, maxlon REAL, maxlat REAL,
    first_date TEXT, last_date TEXT,
    created_at TEXT NOT NULL
    ,priority_tier TEXT DEFAULT 'medium'
    ,priority_geojson TEXT
);

CREATE TABLE IF NOT EXISTS scenes (
    scene_path TEXT PRIMARY KEY,
    aoi_id INTEGER,
    acquisition_date TEXT NOT NULL,
    acquisition_date_source TEXT,       -- how we got the date: json_sensing_time | json_timerange_fallback | geotiff_tag | filename
    sensor TEXT NOT NULL,
    cloud_cover_percent REAL,           -- from real Copernicus metadata, when available
    source_metadata TEXT,               -- raw extracted metadata JSON, full provenance
    ingested_at TEXT NOT NULL,
    FOREIGN KEY (aoi_id) REFERENCES aois(aoi_id)
);

CREATE TABLE IF NOT EXISTS tiles (
    vector_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tile_id TEXT NOT NULL,              -- MGRS ground identifier (shared across dates)
    aoi_id INTEGER,
    scene_path TEXT NOT NULL,
    tile_path TEXT NOT NULL,
    acquisition_date TEXT NOT NULL,
    sensor TEXT NOT NULL,
    row_idx INTEGER, col_idx INTEGER,
    minlon REAL, minlat REAL, maxlon REAL, maxlat REAL,
    ndvi_mean REAL, ndvi_std REAL, ndwi_mean REAL,
    cloud_fraction REAL, snow_fraction REAL, water_fraction REAL,
    valid_pixel_fraction REAL,
    haze_score REAL,
    cluster_id INTEGER,                 -- filled in by Stage 16 discovery
    velocity_trend TEXT,
    latest_velocity REAL,
    land_cover TEXT,
    processing_version TEXT NOT NULL,
    FOREIGN KEY (scene_path) REFERENCES scenes(scene_path)
);
CREATE INDEX IF NOT EXISTS idx_tiles_tile_id ON tiles(tile_id);
CREATE INDEX IF NOT EXISTS idx_tiles_date ON tiles(acquisition_date);

CREATE TABLE IF NOT EXISTS change_candidates (
    candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tile_id TEXT NOT NULL,
    vector_id_before INTEGER NOT NULL,
    vector_id_after INTEGER NOT NULL,
    date_before TEXT NOT NULL,
    date_after TEXT NOT NULL,
    embedding_drift REAL NOT NULL,
    spectral_delta REAL NOT NULL,
    combined_score REAL NOT NULL,
    suppressed INTEGER NOT NULL DEFAULT 0,
    suppression_reason TEXT,
    change_type TEXT,
    change_type_confidence REAL,
    earliest_supported_date TEXT,
    changed_fraction REAL,
    pixel_diff_score REAL,
    change_region TEXT,
    change_centroid_x REAL,
    change_centroid_y REAL,
    narrative TEXT,
    sar_score REAL,
    fused_score REAL,
    sar_only INTEGER DEFAULT 0,
    modality TEXT,
    land_cover TEXT,
    priority_score REAL,
    priority_reasons TEXT,
    predicted_confirm_prob REAL,
    heatmap_spectral TEXT,
    heatmap_attention TEXT,
    llm_narrative TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_candidates_tile ON change_candidates(tile_id);

CREATE TABLE IF NOT EXISTS sar_observations (
    sar_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tile_id TEXT,
    scene_path TEXT NOT NULL,
    acquisition_date TEXT NOT NULL,
    vv_mean REAL,
    vh_mean REAL,
    valid_fraction REAL,
    metadata TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sar_tile_date ON sar_observations(tile_id, acquisition_date);

CREATE TABLE IF NOT EXISTS sar_tiles (
    sar_tile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tile_id TEXT, aoi_id INTEGER, sensor TEXT, product_type TEXT,
    period_start TEXT, period_end TEXT, acquisition_datetime TEXT,
    tile_path TEXT, vv_mean_db REAL, vh_mean_db REAL,
    vv_std_db REAL, vh_std_db REAL, vv_minus_vh_db REAL, valid_pixels REAL,
    speckle_filter_applied INTEGER DEFAULT 0, processing_version TEXT
);
CREATE INDEX IF NOT EXISTS idx_sar_tile_id ON sar_tiles(tile_id);

CREATE TABLE IF NOT EXISTS audit_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER,
    analyst_decision TEXT NOT NULL,      -- 'confirm' | 'reject'
    reason TEXT,
    decided_at TEXT NOT NULL,
    model_version TEXT NOT NULL,
    FOREIGN KEY (candidate_id) REFERENCES change_candidates(candidate_id)
);
"""

PROCESSING_VERSION = "v0.2-innovations"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _existing_columns(conn, table: str) -> set:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _ensure_column(conn, table: str, column: str, coltype: str):
    """SQLite has no 'ADD COLUMN IF NOT EXISTS' in the versions we
    target, so check PRAGMA table_info first. Lets a database created
    by an earlier version of this schema pick up new columns (aoi_id,
    cloud_cover_percent, source_metadata) without deleting existing data."""
    if column not in _existing_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # Migration path for databases created before the aois table /
        # real-metadata columns existed (e.g. from the synthetic-data
        # prototype phase) -- safe to run every time, a no-op once caught up.
        _ensure_column(conn, "scenes", "aoi_id", "INTEGER")
        _ensure_column(conn, "scenes", "acquisition_date_source", "TEXT")
        _ensure_column(conn, "scenes", "cloud_cover_percent", "REAL")
        _ensure_column(conn, "scenes", "source_metadata", "TEXT")
        _ensure_column(conn, "tiles", "aoi_id", "INTEGER")
        _ensure_column(conn, "tiles", "haze_score", "REAL")
        _ensure_column(conn, "tiles", "velocity_trend", "TEXT")
        _ensure_column(conn, "tiles", "latest_velocity", "REAL")
        _ensure_column(conn, "tiles", "land_cover", "TEXT")
        _ensure_column(conn, "aois", "priority_tier", "TEXT DEFAULT 'medium'")
        _ensure_column(conn, "aois", "priority_geojson", "TEXT")
        _ensure_column(conn, "change_candidates", "changed_fraction", "REAL")
        _ensure_column(conn, "change_candidates", "pixel_diff_score", "REAL")
        _ensure_column(conn, "change_candidates", "change_region", "TEXT")
        _ensure_column(conn, "change_candidates", "change_centroid_x", "REAL")
        _ensure_column(conn, "change_candidates", "change_centroid_y", "REAL")
        _ensure_column(conn, "change_candidates", "narrative", "TEXT")
        _ensure_column(conn, "change_candidates", "sar_score", "REAL")
        _ensure_column(conn, "change_candidates", "fused_score", "REAL")
        _ensure_column(conn, "change_candidates", "sar_only", "INTEGER")
        _ensure_column(conn, "change_candidates", "modality", "TEXT")
        _ensure_column(conn, "change_candidates", "land_cover", "TEXT")
        _ensure_column(conn, "change_candidates", "priority_score", "REAL")
        _ensure_column(conn, "change_candidates", "priority_reasons", "TEXT")
        _ensure_column(conn, "change_candidates", "predicted_confirm_prob", "REAL")
        _ensure_column(conn, "change_candidates", "heatmap_spectral", "TEXT")
        _ensure_column(conn, "change_candidates", "heatmap_attention", "TEXT")
        _ensure_column(conn, "change_candidates", "llm_narrative", "TEXT")
        # These indexes reference columns that may have just been added
        # by the migration above, so they can only be created AFTER it --
        # unlike the rest of SCHEMA, they can't live in the initial
        # executescript() for a database that predates the aois table.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tiles_aoi ON tiles(aoi_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scenes_aoi ON scenes(aoi_id)")


def register_sar_observation(*, tile_id: str | None, scene_path: str, acquisition_date: str,
                             vv_mean: float | None = None, vh_mean: float | None = None,
                             valid_fraction: float | None = None, metadata: dict | None = None) -> int:
    """Persist SAR provenance without altering optical scene/tile records."""
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO sar_observations
               (tile_id, scene_path, acquisition_date, vv_mean, vh_mean, valid_fraction, metadata, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (tile_id, scene_path, acquisition_date, vv_mean, vh_mean, valid_fraction,
             json.dumps(metadata) if metadata else None, datetime.now(timezone.utc).isoformat()),
        )
        return cur.lastrowid


def list_sar_observations(tile_id: str | None = None) -> list[sqlite3.Row]:
    with get_conn() as conn:
        if tile_id:
            return conn.execute("SELECT * FROM sar_observations WHERE tile_id=? ORDER BY acquisition_date", (tile_id,)).fetchall()
        return conn.execute("SELECT * FROM sar_observations ORDER BY acquisition_date").fetchall()


# ---- AOI registry --------------------------------------------------------

def get_aoi_by_name(name: str) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM aois WHERE name = ?", (name,)).fetchone()


def get_aoi(aoi_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM aois WHERE aoi_id = ?", (aoi_id,)).fetchone()


def list_aois() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM aois ORDER BY name").fetchall()


def get_or_create_aoi(name: str, source_folder: str = None) -> int:
    """Idempotent -- calling this repeatedly for the same AOI name (e.g.
    re-running onboarding after adding more months to the same folder)
    never creates a duplicate row."""
    existing = get_aoi_by_name(name)
    if existing:
        return existing["aoi_id"]
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO aois (name, source_folder, created_at) VALUES (?, ?, ?)",
            (name, source_folder, datetime.now(timezone.utc).isoformat()),
        )
        return cur.lastrowid


def update_aoi_extent(aoi_id: int):
    """Recomputes the AOI's bounding box and date range from its own
    tiles/scenes. Call this after ingesting new scenes into the AOI --
    cheap enough to just recompute rather than incrementally track."""
    with get_conn() as conn:
        bbox = conn.execute(
            """SELECT MIN(minlon) minlon, MIN(minlat) minlat,
                      MAX(maxlon) maxlon, MAX(maxlat) maxlat
               FROM tiles WHERE aoi_id = ?""", (aoi_id,)
        ).fetchone()
        dates = conn.execute(
            "SELECT MIN(acquisition_date) first_date, MAX(acquisition_date) last_date "
            "FROM scenes WHERE aoi_id = ?", (aoi_id,)
        ).fetchone()
        conn.execute(
            """UPDATE aois SET minlon=?, minlat=?, maxlon=?, maxlat=?,
               first_date=?, last_date=? WHERE aoi_id=?""",
            (bbox["minlon"], bbox["minlat"], bbox["maxlon"], bbox["maxlat"],
             dates["first_date"], dates["last_date"], aoi_id),
        )


def list_scenes(aoi_id: int = None) -> list[sqlite3.Row]:
    with get_conn() as conn:
        if aoi_id is not None:
            return conn.execute(
                "SELECT * FROM scenes WHERE aoi_id = ? ORDER BY acquisition_date", (aoi_id,)
            ).fetchall()
        return conn.execute("SELECT * FROM scenes ORDER BY acquisition_date").fetchall()


def scene_already_ingested(scene_path: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM scenes WHERE scene_path = ?", (scene_path,)
        ).fetchone()
        return row is not None


def purge_scene(scene_path: str) -> dict:
    """Remove one scene and all derived records for controlled reingestion."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT vector_id, tile_path FROM tiles WHERE scene_path = ?", (scene_path,)
        ).fetchall()
        vector_ids = [row["vector_id"] for row in rows]
        if vector_ids:
            placeholders = ",".join("?" for _ in vector_ids)
            candidate_rows = conn.execute(
                f"SELECT candidate_id FROM change_candidates "
                f"WHERE vector_id_before IN ({placeholders}) OR vector_id_after IN ({placeholders})",
                vector_ids + vector_ids,
            ).fetchall()
            candidate_ids = [row["candidate_id"] for row in candidate_rows]
            if candidate_ids:
                candidate_placeholders = ",".join("?" for _ in candidate_ids)
                conn.execute(
                    f"DELETE FROM audit_log WHERE candidate_id IN ({candidate_placeholders})",
                    candidate_ids,
                )
                conn.execute(
                    f"DELETE FROM change_candidates WHERE candidate_id IN ({candidate_placeholders})",
                    candidate_ids,
                )
            conn.execute(f"DELETE FROM tiles WHERE vector_id IN ({placeholders})", vector_ids)
        conn.execute("DELETE FROM scenes WHERE scene_path = ?", (scene_path,))
    return {"vector_ids": vector_ids, "tile_paths": [row["tile_path"] for row in rows]}


def register_scene(scene_path: str, acquisition_date: str, sensor: str, aoi_id: int = None,
                    acquisition_date_source: str = None, cloud_cover_percent: float = None,
                    source_metadata: dict = None):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO scenes (
                scene_path, aoi_id, acquisition_date, acquisition_date_source, sensor,
                cloud_cover_percent, source_metadata, ingested_at
            ) VALUES (?,?,?,?,?,?,?,?)""",
            (scene_path, aoi_id, acquisition_date, acquisition_date_source, sensor,
             cloud_cover_percent, json.dumps(source_metadata) if source_metadata else None,
             datetime.now(timezone.utc).isoformat()),
        )


def insert_tile(tile, features, aoi_id: int = None) -> int:
    """tile: app.geospatial.tiler.Tile, features: app.geospatial.features.TileFeatures.
    Returns the new vector_id -- this integer is exactly what gets handed
    to FAISS as the index id, so SQLite and FAISS never drift apart."""
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO tiles (
                tile_id, aoi_id, scene_path, tile_path, acquisition_date, sensor,
                row_idx, col_idx, minlon, minlat, maxlon, maxlat,
                ndvi_mean, ndvi_std, ndwi_mean, cloud_fraction, snow_fraction,
                water_fraction, valid_pixel_fraction, haze_score, processing_version
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                tile.tile_id, aoi_id, tile.scene_path, tile.tile_path, tile.acquisition_date, tile.sensor,
                tile.row, tile.col, *tile.bbox_wgs84,
                features.ndvi_mean, features.ndvi_std, features.ndwi_mean,
                features.cloud_fraction, features.snow_fraction, features.water_fraction,
                features.valid_pixel_fraction, features.haze_score, PROCESSING_VERSION,
            ),
        )
        return cur.lastrowid


def get_tile(vector_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM tiles WHERE vector_id = ?", (vector_id,)).fetchone()


def get_tiles_by_ids(vector_ids: list[int]) -> list[sqlite3.Row]:
    if not vector_ids:
        return []
    with get_conn() as conn:
        placeholders = ",".join("?" for _ in vector_ids)
        rows = conn.execute(
            f"SELECT * FROM tiles WHERE vector_id IN ({placeholders})", vector_ids
        ).fetchall()
    # preserve the FAISS-returned rank order
    by_id = {r["vector_id"]: r for r in rows}
    return [by_id[v] for v in vector_ids if v in by_id]


def get_tile_history(tile_id: str) -> list[sqlite3.Row]:
    """All observations of one ground cell, chronologically -- what
    Stage 11 temporal pairing iterates over."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM tiles WHERE tile_id = ? ORDER BY acquisition_date ASC",
            (tile_id,),
        ).fetchall()


def get_all_tile_ids(aoi_id: int = None) -> list[str]:
    with get_conn() as conn:
        if aoi_id is not None:
            rows = conn.execute(
                "SELECT DISTINCT tile_id FROM tiles WHERE aoi_id = ?", (aoi_id,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT DISTINCT tile_id FROM tiles").fetchall()
    return [r["tile_id"] for r in rows]


def get_vector_ids_for_aoi(aoi_id: int) -> list[int]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT vector_id FROM tiles WHERE aoi_id = ?", (aoi_id,)
        ).fetchall()
    return [r["vector_id"] for r in rows]


def insert_change_candidate(**kwargs) -> int:
    kwargs["created_at"] = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT candidate_id FROM change_candidates "
            "WHERE tile_id=? AND vector_id_before=? AND vector_id_after=?",
            (kwargs["tile_id"], kwargs["vector_id_before"], kwargs["vector_id_after"]),
        ).fetchone()
        if existing:
            candidate_id = existing["candidate_id"]
            updates = {key: value for key, value in kwargs.items() if key != "created_at"}
            assignments = ",".join(f"{key}=?" for key in updates)
            conn.execute(
                f"UPDATE change_candidates SET {assignments} WHERE candidate_id=?",
                (*updates.values(), candidate_id),
            )
            return candidate_id
        cols = ",".join(kwargs.keys())
        placeholders = ",".join("?" for _ in kwargs)
        cur = conn.execute(
            f"INSERT INTO change_candidates ({cols}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        )
        return cur.lastrowid


def list_review_queue(include_suppressed: bool = False, limit: int = 50, aoi_id: int = None) -> list[sqlite3.Row]:
    """aoi_id filters via a join against tiles (change_candidates itself
    is aoi-agnostic, keyed only on tile_id) -- convenient for the
    frontend's GET /change/candidates?aoi_id= filter."""
    q = """SELECT cc.* FROM change_candidates cc
           JOIN tiles t ON t.tile_id = cc.tile_id AND t.vector_id = cc.vector_id_after"""
    conditions, params = [], []
    if not include_suppressed:
        conditions.append("cc.suppressed = 0")
    if aoi_id is not None:
        conditions.append("t.aoi_id = ?")
        params.append(aoi_id)
    if conditions:
        q += " WHERE " + " AND ".join(conditions)
    q += " ORDER BY cc.combined_score DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        return conn.execute(q, params).fetchall()


def record_decision(candidate_id: int, decision: str, reason: str = None):
    assert decision in ("confirm", "reject")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (candidate_id, analyst_decision, reason, decided_at, model_version) "
            "VALUES (?,?,?,?,?)",
            (candidate_id, decision, reason, datetime.now(timezone.utc).isoformat(), PROCESSING_VERSION),
        )


def set_tile_cluster(vector_id: int, cluster_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE tiles SET cluster_id = ? WHERE vector_id = ?", (cluster_id, vector_id))


def clear_tile_clusters():
    with get_conn() as conn:
        conn.execute("UPDATE tiles SET cluster_id = NULL")
