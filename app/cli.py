"""
Single command-line entry point for every stage of the pipeline.
This is deliberately a thin dispatcher -- all real logic lives in
app/*, so this file is what changes least when you later wrap the
same functions in FastAPI endpoints.

Usage:
    python -m app.cli ingest data/raw/aoi_2025-01-15.tif 2025-01-15 SENTINEL2_SYNTHETIC
    python -m app.cli detect-changes
    python -m app.cli cluster
    python -m app.cli search-text "newly built structures near a river"
    python -m app.cli review-queue
    python -m app.cli decide 5 confirm
    python -m app.cli stats
"""
import argparse
import json
import logging
import platform
from pathlib import Path
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def cmd_ingest(args):
    from app.pipeline.ingest import ingest_scene
    t0 = time.time()
    result = ingest_scene(args.scene_path, args.date, args.sensor)
    result["seconds"] = round(time.time() - t0, 2)
    print(json.dumps(result, indent=2))


def cmd_reingest(args):
    from app.geospatial import catalog_db as db
    from app.index.vector_index import VectorIndex
    from app.pipeline.ingest import ingest_scene

    scene_path = str(Path(args.scene_path))
    with db.get_conn() as conn:
        existing = conn.execute("SELECT * FROM scenes WHERE scene_path = ?", (scene_path,)).fetchone()
    if existing is None:
        raise ValueError(f"Scene is not registered and cannot be reingested: {scene_path}")
    metadata = json.loads(existing["source_metadata"]) if existing["source_metadata"] else None
    removed = db.purge_scene(scene_path)
    for tile_path in removed["tile_paths"]:
        Path(tile_path).unlink(missing_ok=True)
    index = VectorIndex()
    index.remove(removed["vector_ids"])
    index.save()
    result = ingest_scene(
        scene_path,
        existing["acquisition_date"],
        existing["sensor"],
        aoi_id=existing["aoi_id"],
        acquisition_date_source=existing["acquisition_date_source"],
        cloud_cover_percent=existing["cloud_cover_percent"],
        source_metadata=metadata,
    )
    result.update({"removed_vectors": len(removed["vector_ids"]), "removed_tiles": len(removed["tile_paths"])})
    print(json.dumps(result, indent=2))


def cmd_detect_changes(args):
    from app.change.detector import run_change_detection_for_all_tiles
    from app.change.classifier import classify_change_type
    from app.geospatial import catalog_db as db

    promoted_ids = run_change_detection_for_all_tiles(threshold=args.threshold)
    print(f"Promoted {len(promoted_ids)} candidates past suppression (threshold={args.threshold})")

    if args.classify:
        with db.get_conn() as conn:
            for cid in promoted_ids:
                row = conn.execute(
                    "SELECT * FROM change_candidates WHERE candidate_id = ?", (cid,)
                ).fetchone()
                after_tile = db.get_tile(row["vector_id_after"])
                result = classify_change_type(after_tile["tile_path"])
                conn.execute(
                    "UPDATE change_candidates SET change_type=?, change_type_confidence=? WHERE candidate_id=?",
                    (result.change_type, result.confidence, cid),
                )
                print(f"  candidate {cid}: {result.change_type} ({result.confidence:.2f})")


def cmd_cluster(args):
    from app.discovery.clustering import cluster_all_tiles
    assignment = cluster_all_tiles(min_cluster_size=args.min_cluster_size)
    n_clusters = len(set(assignment.values()) - {-1})
    n_noise = sum(1 for v in assignment.values() if v == -1)
    print(f"Clustered {len(assignment)} tiles into {n_clusters} clusters ({n_noise} unclustered/noise)")


def cmd_search_text(args):
    from app.index.search import text_search
    results = text_search(args.query, top_k=args.top_k)
    for r in results:
        print(f"{r.similarity:.4f}  {r.tile_id}  {r.acquisition_date}  {r.tile_path}")


def cmd_validate_remoteclip(args):
    import numpy as np
    from app.config import CLIP_DEVICE, EMBEDDING_DIM, REMOTECLIP_CHECKPOINT, REMOTECLIP_LICENSE, REMOTECLIP_ORIGIN, validate_remoteclip_config
    from app.embeddings.clip_embedder import embed_image_tile, embed_text
    from app.geospatial import catalog_db as db
    from app.index.vector_index import VectorIndex

    checkpoint_path = validate_remoteclip_config()
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT vector_id, tile_id, tile_path FROM tiles WHERE tile_path IS NOT NULL ORDER BY vector_id"
        ).fetchall()
    real_tiles = [row for row in rows if Path(row["tile_path"]).is_file()]
    if len(real_tiles) < 12:
        raise RuntimeError("Fewer than twelve real satellite tiles with existing local paths are available for validation.")

    sample_tiles = real_tiles[:12]
    first_tile, second_tile = sample_tiles[:2]
    image_vector = embed_image_tile(first_tile["tile_path"])
    repeated_vector = embed_image_tile(first_tile["tile_path"])
    different_image_vector = embed_image_tile(second_tile["tile_path"])
    sample_vectors = [embed_image_tile(row["tile_path"]) for row in sample_tiles]
    text_vector = embed_text("satellite construction development")
    index = VectorIndex()
    checks = {
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_format": checkpoint_path.suffix.lower(),
        "origin": REMOTECLIP_ORIGIN,
        "license": REMOTECLIP_LICENSE,
        "model": "RemoteCLIP-ViT-B-32",
        "architecture": "ViT-B-32",
        "device": CLIP_DEVICE,
        "real_tiles": [row["tile_path"] for row in sample_tiles],
        "real_tile_count": len(sample_vectors),
        "real_vector_ids": [int(row["vector_id"]) for row in sample_tiles],
        "image_dimension": int(image_vector.shape[0]),
        "text_dimension": int(text_vector.shape[0]),
        "finite_values": bool(np.isfinite(image_vector).all() and np.isfinite(text_vector).all()),
        "embedding_dimension": EMBEDDING_DIM,
        "faiss_dimension": index.index.d,
        "faiss_vector_count": index.ntotal,
        "image_normalized": bool(np.isclose(np.linalg.norm(image_vector), 1.0, atol=1e-4)),
        "text_normalized": bool(np.isclose(np.linalg.norm(text_vector), 1.0, atol=1e-4)),
        "repeat_cosine_similarity": float(np.dot(image_vector, repeated_vector)),
        "different_image_cosine_similarity": float(np.dot(image_vector, different_image_vector)),
        "sample_finite": bool(all(np.isfinite(vector).all() for vector in sample_vectors)),
        "sample_normalized": bool(all(np.isclose(np.linalg.norm(vector), 1.0, atol=1e-4) for vector in sample_vectors)),
    }
    checks["deterministic_repeat"] = bool(checks["repeat_cosine_similarity"] > 0.9999)
    checks["dimension_compatible"] = bool(
        checks["image_dimension"] == checks["text_dimension"] == index.index.d == EMBEDDING_DIM
    )
    if not (checks["finite_values"] and checks["image_normalized"] and checks["text_normalized"] and checks["deterministic_repeat"]):
        raise RuntimeError(f"RemoteCLIP controlled validation failed: {checks}")
    if not checks["dimension_compatible"]:
        raise RuntimeError(f"Embedding/FAISS dimension mismatch: {checks}")
    print(json.dumps(checks, indent=2))


def cmd_migrate_remoteclip(args):
    from app.index.remoteclip_migration import migrate, replace_validated_index

    report = migrate()
    print(json.dumps(report, indent=2))
    if args.replace:
        print(json.dumps(replace_validated_index(), indent=2))


def cmd_diagnose_source(args):
    import numpy as np
    import rasterio
    from app.geospatial import catalog_db as db

    def print_tile_diagnostics(tile_path: str | None, label: str):
        print(f"{label} tile_path: {tile_path}")
        path = Path(tile_path) if tile_path else None
        exists = bool(path and path.exists())
        print(f"  Path.exists(): {exists}")
        if not exists:
            print("  rasterio.open(): not attempted (file missing)")
            return
        try:
            with rasterio.open(path) as source:
                print("  rasterio.open(): success")
                print(f"  source.count: {source.count}")
                if source.count < 4:
                    print("  FAIL: source.count < 4")
                    return
                bands = source.read([1, 2, 3, 4], masked=True)
                for index, band in enumerate(bands[:4], start=1):
                    values = band.compressed()
                    empty = values.size == 0
                    finite_any = bool(np.isfinite(values).any()) if values.size else False
                    nonzero_any = bool(np.any(values != 0)) if values.size else False
                    print(f"  Band {index}: compressed={len(values)} values, empty={empty}, any_finite={finite_any}, any_nonzero={nonzero_any}")
                    if empty:
                        print(f"    FAIL: band {index} is empty/compressed() == []")
                    if values.size and not finite_any:
                        print(f"    FAIL: band {index} has no finite values")
                    if values.size and not nonzero_any:
                        print(f"    FAIL: band {index} is all zero / nodata")
            print(f"  has_valid_multispectral_data({path}): {__import__('app.geospatial.rendering', fromlist=['has_valid_multispectral_data']).has_valid_multispectral_data(path)}")
        except Exception as exc:  # pragma: no cover
            print(f"  rasterio.open(): failed: {exc}")

    if args.candidate_id is not None:
        with db.get_conn() as conn:
            row = conn.execute("SELECT * FROM change_candidates WHERE candidate_id = ?", (args.candidate_id,)).fetchone()
        if row is None:
            raise ValueError(f"Candidate {args.candidate_id} not found")
        before = db.get_tile(row["vector_id_before"])
        if before is None:
            raise ValueError(f"Candidate {args.candidate_id} references a missing before tile vector_id={row['vector_id_before']}")
        print(f"Candidate #{row['candidate_id']} :: before_date={row['date_before']} after_date={row['date_after']} tile_id={row['tile_id']}")
        print_tile_diagnostics(before["tile_path"], "Before")
        after = db.get_tile(row["vector_id_after"])
        if after is not None:
            print_tile_diagnostics(after["tile_path"], "After")
        return

    if args.tile_id is not None:
        with db.get_conn() as conn:
            row = conn.execute("SELECT * FROM tiles WHERE tile_id = ? ORDER BY acquisition_date DESC LIMIT 1", (args.tile_id,)).fetchone()
        if row is None:
            raise ValueError(f"Tile {args.tile_id} not found")
        print(f"Tile {row['tile_id']} :: date={row['acquisition_date']} scene_path={row['scene_path']}")
        print_tile_diagnostics(row["tile_path"], "Tile")
        return

    raise ValueError("Specify either --candidate-id or --tile-id")


def cmd_review_queue(args):
    from app.review.queue import get_review_queue
    for item in get_review_queue(limit=args.limit):
        print(f"[{item.candidate_id}] {item.tile_id} {item.date_before}->{item.date_after} "
              f"score={item.combined_score:.3f} type={item.change_type}")


def cmd_decide(args):
    from app.review.queue import submit_decision
    submit_decision(args.candidate_id, args.decision, reason=args.reason)
    print(f"Recorded '{args.decision}' for candidate {args.candidate_id}")


def cmd_stats(args):
    from app.geospatial import catalog_db as db
    from app.index.vector_index import VectorIndex
    with db.get_conn() as conn:
        n_scenes = conn.execute("SELECT COUNT(*) c FROM scenes").fetchone()["c"]
        n_tiles = conn.execute("SELECT COUNT(*) c FROM tiles").fetchone()["c"]
        n_candidates = conn.execute("SELECT COUNT(*) c FROM change_candidates").fetchone()["c"]
        n_promoted = conn.execute("SELECT COUNT(*) c FROM change_candidates WHERE suppressed=0").fetchone()["c"]
    index = VectorIndex()
    print(json.dumps({
        "scenes_ingested": n_scenes,
        "tiles_indexed": n_tiles,
        "faiss_ntotal": index.ntotal,
        "change_candidates_scored": n_candidates,
        "change_candidates_promoted": n_promoted,
    }, indent=2))


def cmd_add_aoi(args):
    from app.pipeline.onboard_aoi import onboard_aoi, print_onboard_report
    report = onboard_aoi(args.aoi_name, args.source_folder, sensor=args.sensor)
    print_onboard_report(report)


def cmd_inspect_zip(args):
    from app.geospatial.copernicus_metadata import inspect_zip
    info = inspect_zip(args.zip_path)
    print("Files inside zip:")
    for f in info["files"]:
        print(" -", f)
    print("\nParsed JSON contents:")
    print(json.dumps(info["json_contents"], indent=2))


def cmd_list_aois(args):
    from app.geospatial import catalog_db as db
    for aoi in db.list_aois():
        print(dict(aoi))


def cmd_calibrate(args):
    from app.change.calibration import calibrate_from_audit
    print(json.dumps(calibrate_from_audit(), indent=2))


def cmd_eval_report(args):
    import hashlib
    from app.config import CLIP_DEVICE, DATA_DIR, CLIP_MODEL_NAME, EMBEDDING_DIM, REMOTECLIP_CHECKPOINT
    from app.geospatial import catalog_db as db
    from app.index.vector_index import VectorIndex

    report_path = DATA_DIR / "evaluation_report.md"
    with db.get_conn() as conn:
        counts = {
            "aois": conn.execute("SELECT COUNT(*) FROM aois").fetchone()[0],
            "scenes": conn.execute("SELECT COUNT(*) FROM scenes").fetchone()[0],
            "tiles": conn.execute("SELECT COUNT(*) FROM tiles").fetchone()[0],
            "candidates": conn.execute("SELECT COUNT(*) FROM change_candidates").fetchone()[0],
            "promoted": conn.execute("SELECT COUNT(*) FROM change_candidates WHERE suppressed=0").fetchone()[0],
            "suppressed": conn.execute("SELECT COUNT(*) FROM change_candidates WHERE suppressed=1").fetchone()[0],
            "confirmed": conn.execute("SELECT COUNT(*) FROM audit_log WHERE analyst_decision='confirm'").fetchone()[0],
            "rejected": conn.execute("SELECT COUNT(*) FROM audit_log WHERE analyst_decision='reject'").fetchone()[0],
        }
        clusters = conn.execute("SELECT cluster_id, COUNT(*) n FROM tiles WHERE cluster_id IS NOT NULL AND cluster_id != -1 GROUP BY cluster_id ORDER BY cluster_id").fetchall()
        invalid = 0
        for row in conn.execute("SELECT DISTINCT scene_path FROM scenes").fetchall():
            invalid += int(not Path(row[0]).exists())
    index = VectorIndex()
    migration_path = DATA_DIR / "index" / "remoteclip_migration_report.json"
    migration = json.loads(migration_path.read_text(encoding="utf-8")) if migration_path.exists() else {}
    old_index_path = DATA_DIR / "migration_backup_20260908" / "tiles.faiss.old"
    checkpoint_hash = hashlib.sha256(REMOTECLIP_CHECKPOINT.read_bytes()).hexdigest() if REMOTECLIP_CHECKPOINT.is_file() else None
    storage_bytes = sum(path.stat().st_size for path in DATA_DIR.rglob("*") if path.is_file())
    lines = [
        "# Satellite Intelligence Evaluation Report", "", "## Real data", 
        f"- AOIs: {counts['aois']}", f"- Scenes: {counts['scenes']}", f"- Tiles: {counts['tiles']}",
        f"- FAISS vectors: {index.ntotal}", f"- Eligible tiles: {migration.get('eligible_tile_count', 'NOT MEASURED')}",
        f"- Successful embeddings: {migration.get('successful_embedding_count', 'NOT MEASURED')}",
        f"- Failed/skipped tiles: {migration.get('failed_or_skipped_count', 'NOT MEASURED')}", f"- Invalid/missing scene paths: {invalid}",
        "- Indexed area: NOT MEASURED (catalog has no area aggregate)", f"- Storage: {storage_bytes / (1024 ** 2):.2f} MiB",
        "", "## Processing", "- Ingestion/build timing: NOT MEASURED (not recorded in catalog)",
        f"- Hardware: {platform.platform()}", f"- Python executable: {sys.executable}", f"- Python version: {platform.python_version()}",
        f"- Device: {CLIP_DEVICE}", f"- Model: RemoteCLIP-{CLIP_MODEL_NAME}", f"- Checkpoint: {REMOTECLIP_CHECKPOINT}",
        f"- Checkpoint status: {'AVAILABLE' if REMOTECLIP_CHECKPOINT.is_file() else 'CHECKPOINT UNAVAILABLE'}", f"- Checkpoint SHA-256: {checkpoint_hash or 'NOT MEASURED'}", f"- Embedding dimension: {EMBEDDING_DIM}",
        f"- Previous FAISS SHA-256: {hashlib.sha256(old_index_path.read_bytes()).hexdigest() if old_index_path.is_file() else 'NOT MEASURED'}", f"- Current FAISS SHA-256: {hashlib.sha256((DATA_DIR / 'index' / 'tiles.faiss').read_bytes()).hexdigest()}",
        "", "## Change detection", f"- Candidates scored: {counts['candidates']}", f"- Promoted: {counts['promoted']}",
        f"- Suppressed: {counts['suppressed']}", f"- Confirmed audit decisions: {counts['confirmed']}", f"- Rejected audit decisions: {counts['rejected']}",
        "- Search latency p50: NOT MEASURED", "- Search latency p95: NOT MEASURED", "- Retrieval relevance labels: INSUFFICIENT REAL DATA", "- Precision@K / Recall@K / MRR: NOT MEASURED",
        "", "## Clustering", f"- Visible clusters: {len(clusters)}", f"- Members per cluster: {', '.join(f'{row[0]}={row[1]}' for row in clusters) or 'none'}",
        "", "## Data quality", "- SCL availability: measured per tile but not aggregated in the catalog", "- Quality suppression breakdown: available from GET /changes/candidates/data-quality",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(report_path))


def main():
    parser = argparse.ArgumentParser(description="Satellite Intelligence pipeline CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="Ingest one GeoTIFF/COG scene")
    p.add_argument("scene_path")
    p.add_argument("date", help="Acquisition date, e.g. 2025-06-10")
    p.add_argument("sensor", help="e.g. SENTINEL2")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("reingest", help="Purge and reingest one already registered repaired scene")
    p.add_argument("scene_path")
    p.set_defaults(func=cmd_reingest)

    p = sub.add_parser("detect-changes", help="Run temporal change detection over all ingested tiles")
    p.add_argument("--threshold", type=float, default=0.22)
    p.add_argument("--classify", action="store_true", default=True, help="Run zero-shot change-type classification (default)")
    p.set_defaults(func=cmd_detect_changes)

    p = sub.add_parser("cluster", help="Run discovery clustering over all indexed tiles")
    p.add_argument("--min-cluster-size", dest="min_cluster_size", type=int, default=3)
    p.set_defaults(func=cmd_cluster)

    p = sub.add_parser("search-text", help="Semantic text search")
    p.add_argument("query")
    p.add_argument("--top-k", dest="top_k", type=int, default=10)
    p.set_defaults(func=cmd_search_text)

    p = sub.add_parser("validate-remoteclip", help="Validate the staged RemoteCLIP checkpoint against real imagery and FAISS")
    p.set_defaults(func=cmd_validate_remoteclip)

    p = sub.add_parser("migrate-remoteclip", help="Re-embed real eligible tiles into a validated temporary RemoteCLIP FAISS index")
    p.add_argument("--replace", action="store_true", help="Atomically replace production FAISS after temporary validation")
    p.set_defaults(func=cmd_migrate_remoteclip)

    p = sub.add_parser("diagnose-source", help="Inspect the stored tile path and multispectral validity for a candidate or tile")
    p.add_argument("--candidate-id", type=int)
    p.add_argument("--tile-id")
    p.set_defaults(func=cmd_diagnose_source)

    p = sub.add_parser("review-queue", help="List unresolved change candidates")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_review_queue)

    p = sub.add_parser("decide", help="Confirm or reject a change candidate")
    p.add_argument("candidate_id", type=int)
    p.add_argument("decision", choices=["confirm", "reject"])
    p.add_argument("--reason", default=None)
    p.set_defaults(func=cmd_decide)

    p = sub.add_parser("stats", help="Print pipeline / evaluation-report numbers")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("add-aoi", help="Onboard a brand-new AOI from a folder of Copernicus zips or tifs")
    p.add_argument("aoi_name", help="e.g. dholera, site2, site3")
    p.add_argument("source_folder", help="Folder containing .zip (Copernicus export) and/or .tif files")
    p.add_argument("--sensor", default="SENTINEL2_L2A")
    p.set_defaults(func=cmd_add_aoi)

    p = sub.add_parser("inspect-zip", help="Debug: show every file + parsed JSON inside one Copernicus zip")
    p.add_argument("zip_path")
    p.set_defaults(func=cmd_inspect_zip)

    p = sub.add_parser("list-aois", help="List every onboarded AOI and its date/bbox extent")
    p.set_defaults(func=cmd_list_aois)

    p = sub.add_parser("calibrate", help="Fit a threshold from real analyst audit decisions")
    p.set_defaults(func=cmd_calibrate)

    p = sub.add_parser("eval-report", help="Write a measured evaluation report from the live catalog")
    p.set_defaults(func=cmd_eval_report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
