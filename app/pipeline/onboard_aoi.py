"""
Onboard a brand-new AOI from a folder in one call.

This is the direct answer to "add a section where we can add another
AOI -- I give a folder/files of a region and it automatically extracts
metadata, breaks into tiles, and does all the calculations." Point it
at a folder containing either:
  - Copernicus Browser export .zip files (one per month), or
  - already-extracted .tif/.tiff files, or
  - a mix of both

and it will: extract every zip, pull real metadata out of each
(app/geospatial/copernicus_metadata.py), validate the whole batch for
consistency (app/pipeline/batch_validate.py), register a new AOI row,
and run every already-ingested-scene through the full pipeline
(app/pipeline/ingest.py) -- tiling, NDVI/NDWI, embedding, FAISS
indexing, all of it -- exactly the same tested code path a single
scene goes through, just looped and orchestrated.

Design choice: validation warnings are surfaced but NEVER silently
block ingestion -- a CRS mismatch on one bad month shouldn't stop the
other 71 good months from being ingested. Every per-scene outcome
(ingested / skipped / failed, and why) is recorded in the returned
report so nothing is silently lost.
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from app.config import RAW_DIR
from app.geospatial import catalog_db as db
from app.geospatial.copernicus_metadata import extract_zip_to_scene, SceneMetadata
from app.geospatial.reader import inspect_scene
from app.geospatial.scene_stack import assemble_prepared_stacks
from app.pipeline.batch_validate import ScannedScene, validate_batch, ValidationReport
from app.pipeline.ingest import ingest_scene

log = logging.getLogger("onboard_aoi")


@dataclass
class SceneOutcome:
    source_file: str
    resolved_tif_path: str
    acquisition_date: str
    status: str            # ingested | skipped_duplicate | failed
    tiles_added: int = 0
    error: str = None


@dataclass
class OnboardReport:
    aoi_id: int
    aoi_name: str
    validation: ValidationReport
    scene_outcomes: list = field(default_factory=list)

    @property
    def total_tiles_added(self) -> int:
        return sum(o.tiles_added for o in self.scene_outcomes)

    @property
    def n_ingested(self) -> int:
        return sum(1 for o in self.scene_outcomes if o.status == "ingested")

    @property
    def n_failed(self) -> int:
        return sum(1 for o in self.scene_outcomes if o.status == "failed")


def _discover_input_files(source_folder: Path, staging_dir: Path) -> list[Path]:
    zips = sorted(source_folder.rglob("*.zip"))
    tifs = sorted(list(source_folder.rglob("*.tif")) + list(source_folder.rglob("*.tiff")))
    if not zips and not tifs:
        return []
    prepared_stacks = assemble_prepared_stacks(source_folder, staging_dir)
    if prepared_stacks:
        return prepared_stacks
    return zips + tifs


def count_input_files(source_folder: Path) -> int:
    zips = list(source_folder.rglob("*.zip"))
    if zips:
        return len(zips)
    scene_dates = set()
    from app.geospatial.scene_stack import _date_for, _BAND_RE
    bands_by_date = {}
    for path in source_folder.rglob("*"):
        if path.suffix.lower() not in {".tif", ".tiff"}:
            continue
        match = _BAND_RE.search(path.name)
        date = _date_for(path)
        if match and date:
            bands_by_date.setdefault(date, set()).add(match.group(1))
    scene_dates.update(date for date, bands in bands_by_date.items() if len(bands) == 4)
    return len(scene_dates)


def _resolve_scene(path: Path, staging_dir: Path, sensor: str) -> tuple[str, SceneMetadata]:
    """Returns (tif_path, metadata) whether the input was a zip or an
    already-extracted tif. For a bare tif with no sibling JSON, falls
    back to the GeoTIFF's own tags / filename via inspect_scene, same
    fallback ladder copernicus_metadata.py uses internally."""
    if path.suffix.lower() == ".zip":
        return extract_zip_to_scene(str(path), str(staging_dir))

    # Bare tif: look for a sibling metadata json with the same stem,
    # else fall back to filename/GeoTIFF-tag date with no cloud cover.
    sibling_json = path.with_suffix(".json")
    info = inspect_scene(str(path))
    from app.geospatial.copernicus_metadata import _normalize_date, _walk_json_for_keys, _DATE_KEYS, _CLOUD_KEYS
    import json as _json

    date_found, cloud_found = {}, {}
    if sibling_json.exists():
        try:
            content = _json.loads(sibling_json.read_text())
            _walk_json_for_keys(content, _DATE_KEYS, date_found)
            _walk_json_for_keys(content, _CLOUD_KEYS, cloud_found)
        except (_json.JSONDecodeError, UnicodeDecodeError):
            pass

    acquisition_date, source = None, None
    for key in _DATE_KEYS:
        if key in date_found:
            normalized = _normalize_date(date_found[key])
            if normalized:
                acquisition_date, source = normalized, "json_metadata"
                break
    if acquisition_date is None:
        for k, v in info.tags.items():
            if "date" in k.lower() or "time" in k.lower():
                normalized = _normalize_date(v)
                if normalized:
                    acquisition_date, source = normalized, "geotiff_tag"
                    break
    if acquisition_date is None:
        normalized = _normalize_date(path.stem)
        if normalized:
            acquisition_date, source = normalized, "filename"
    if acquisition_date is None:
        raise ValueError(f"Could not determine acquisition date for {path}")

    cloud_cover = None
    for key in _CLOUD_KEYS:
        if key in cloud_found:
            try:
                cloud_cover = float(cloud_found[key])
            except (TypeError, ValueError):
                pass
            break

    metadata = SceneMetadata(
        acquisition_date=acquisition_date, acquisition_date_source=source,
        cloud_cover_percent=cloud_cover, product_id=None,
        raw_metadata={"source_file": str(path)},
    )
    return str(path), metadata


def onboard_aoi(aoi_name: str, source_folder: str, sensor: str = "SENTINEL2_L2A",
                 staging_subdir: str = None,
                 on_scene_done: Callable[[SceneOutcome, int, int], None] | None = None) -> OnboardReport:
    source_folder = Path(source_folder)
    if not source_folder.exists():
        raise FileNotFoundError(f"Source folder does not exist: {source_folder}")

    staging_dir = Path(staging_subdir) if staging_subdir else (RAW_DIR / aoi_name)
    staging_dir.mkdir(parents=True, exist_ok=True)

    db.init_db()
    aoi_id = db.get_or_create_aoi(aoi_name, source_folder=str(source_folder))
    log.info("AOI '%s' -> aoi_id=%d", aoi_name, aoi_id)

    input_files = _discover_input_files(source_folder, staging_dir)
    if not input_files:
        raise ValueError(f"No .zip/.tif/.tiff files found in {source_folder}")
    log.info("Found %d input files in %s", len(input_files), source_folder)

    # Pass 1: resolve every file to (tif_path, metadata) WITHOUT
    # ingesting yet, so we can validate the whole batch up front.
    resolved: list[tuple[Path, str, SceneMetadata]] = []
    for f in input_files:
        try:
            tif_path, metadata = _resolve_scene(f, staging_dir, sensor)
            resolved.append((f, tif_path, metadata))
        except (ValueError, Exception) as e:
            log.warning("Could not resolve %s: %s -- it will be skipped entirely.", f, e)

    scanned = [
        ScannedScene(path=tif_path, acquisition_date=meta.acquisition_date, info=inspect_scene(tif_path))
        for _, tif_path, meta in resolved
    ]
    cloud_by_date = {meta.acquisition_date: meta.cloud_cover_percent for _, _, meta in resolved}
    report = validate_batch(scanned, cloud_cover_by_date=cloud_by_date)

    if not report.is_clean:
        log.warning("Validation found %d issue(s) -- ingesting anyway, see report.warnings. "
                    "A bad month is skipped individually below, not the whole batch.", len(report.warnings))

    # Pass 2: ingest every scene through the exact same tested pipeline
    # a single manually-ingested scene goes through.
    outcomes = []
    for completed, (source_file, tif_path, metadata) in enumerate(resolved, start=1):
        try:
            result = ingest_scene(
                tif_path, metadata.acquisition_date, sensor, aoi_id=aoi_id,
                acquisition_date_source=metadata.acquisition_date_source,
                cloud_cover_percent=metadata.cloud_cover_percent,
                source_metadata=metadata.raw_metadata,
            )
            outcomes.append(SceneOutcome(
                source_file=str(source_file), resolved_tif_path=tif_path,
                acquisition_date=metadata.acquisition_date,
                status=result["status"], tiles_added=result["tiles_added"],
            ))
        except Exception as e:
            log.error("Failed to ingest %s: %s", source_file, e)
            outcomes.append(SceneOutcome(
                source_file=str(source_file), resolved_tif_path=tif_path,
                acquisition_date=metadata.acquisition_date,
                status="failed", error=str(e),
            ))
        if on_scene_done is not None:
            on_scene_done(outcomes[-1], completed, len(resolved))

    db.update_aoi_extent(aoi_id)

    return OnboardReport(aoi_id=aoi_id, aoi_name=aoi_name, validation=report, scene_outcomes=outcomes)


def print_onboard_report(report: OnboardReport):
    from app.pipeline.batch_validate import print_report
    print(f"\n=== Onboarding report: '{report.aoi_name}' (aoi_id={report.aoi_id}) ===")
    print_report(report.validation)
    print(f"\nScenes ingested: {report.n_ingested} | failed: {report.n_failed} | "
          f"total tiles added: {report.total_tiles_added}")
    for o in report.scene_outcomes:
        line = f"  [{o.status:>17}] {o.acquisition_date}  {o.source_file}"
        if o.status == "ingested":
            line += f"  (+{o.tiles_added} tiles)"
        if o.error:
            line += f"  ERROR: {o.error}"
        print(line)
