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
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import mgrs as mgrs_lib
import rasterio
from rasterio.warp import transform as warp_transform

from app.config import RAW_DIR
from app.geospatial import catalog_db as db
from app.geospatial.copernicus_metadata import extract_zip_to_scene, SceneMetadata
from app.geospatial.reader import inspect_scene
from app.geospatial.scene_stack import assemble_prepared_stacks
from app.pipeline.batch_validate import ScannedScene, validate_batch, ValidationReport
from app.pipeline.ingest import ingest_scene
from app.config import validate_remoteclip_config

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


@dataclass
class SarOutcome:
    source_file: str
    resolved_tif_path: str
    acquisition_date: str | None
    status: str  # ingested | skipped | failed
    product_type: str | None = None
    tile_id: str | None = None
    error: str | None = None


@dataclass
class SarOnboardReport:
    aoi_id: int
    aoi_name: str
    outcomes: list[SarOutcome] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def n_ingested(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.status == "ingested")

    @property
    def n_failed(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.status == "failed")

    @property
    def n_skipped(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.status == "skipped")


def infer_sar_metadata(path: str | Path, *, product_type: str | None = None,
                       date: str | None = None, period_start: str | None = None,
                       period_end: str | None = None,
                       acquisition_datetime: str | None = None) -> dict:
    """Apply the same SAR metadata inference to CLI and folder onboarding."""
    path = Path(path)
    with rasterio.open(path) as source:
        tags = {**source.tags(), **source.tags(1)}
        if source.count >= 2:
            tags.update(source.tags(2))

    def first(*names):
        return next((tags[name] for name in names if tags.get(name)), None)

    resolved_product = (product_type or first("PRODUCT_TYPE", "PRODUCT") or
                        ("IW_MONTHLY_MOSAIC" if any(part in {"mosaic", "monthly_mosaic"} for part in {p.lower() for p in path.parts}) else "GRD")).upper()
    resolved_datetime = acquisition_datetime or first("ACQUISITION_DATETIME", "DATETIME", "SENSING_TIME")
    resolved_start = period_start or first("PERIOD_START", "START_DATE")
    resolved_end = period_end or first("PERIOD_END", "END_DATE")
    resolved_date = date or resolved_datetime or resolved_start
    if not resolved_date:
        match = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
        resolved_date = match.group(1) if match else None
    if not resolved_date and resolved_product == "GRD":
        raise ValueError("could not infer a GRD acquisition date")
    if resolved_product == "IW_MONTHLY_MOSAIC" and not (resolved_start and resolved_end):
        match = re.search(r"(\d{4}-\d{2}-\d{2}).*?(\d{4}-\d{2}-\d{2})", path.name)
        if match:
            resolved_start, resolved_end = match.groups()
        else:
            raise ValueError("monthly mosaic requires start and end dates")
    return {
        "tags": tags,
        "product_type": resolved_product,
        "date": resolved_date,
        "period_start": resolved_start or resolved_date,
        "period_end": resolved_end or resolved_date,
        "acquisition_datetime": resolved_datetime or resolved_date,
    }


def _sar_pairs(source_folder: Path, staging_dir: Path) -> list[tuple[str, Path | None]]:
    files = sorted(path for path in source_folder.rglob("*") if path.suffix.lower() in {".tif", ".tiff"})
    groups: dict[str, dict[str, Path]] = {}
    for path in files:
        name = path.name.lower()
        if "ratio" in name or "rgb" in name:
            yield (str(path), None)
            continue
        polarization = "vv" if "_vv_" in name or name.endswith("_vv.tif") or name.endswith("_vv.tiff") else "vh" if "_vh_" in name or name.endswith("_vh.tif") or name.endswith("_vh.tiff") else None
        if polarization:
            key = re.sub(r"_v[hv](_\(raw\))?", "", path.stem, flags=re.IGNORECASE)
            groups.setdefault(key, {})[polarization] = path
            continue
        try:
            with rasterio.open(path) as source:
                if source.count >= 2:
                    yield_source = path
                else:
                    yield_source = None
        except Exception:
            yield_source = None
        if yield_source is not None:
            yield (str(path), yield_source)
        elif polarization is None:
            yield (str(path), None)

    staging_dir.mkdir(parents=True, exist_ok=True)
    for key, pair in groups.items():
        if "vv" not in pair or "vh" not in pair:
            for path in pair.values():
                yield (str(path), None)
            continue
        stacked = staging_dir / f"{key}_VVVH.tif"
        with rasterio.open(pair["vv"]) as vv_source, rasterio.open(pair["vh"]) as vh_source:
            if (vv_source.width, vv_source.height, vv_source.transform, vv_source.crs) != (vh_source.width, vh_source.height, vh_source.transform, vh_source.crs):
                continue
            profile = vv_source.profile.copy()
            profile.update(count=2, dtype=vv_source.dtypes[0])
            with rasterio.open(stacked, "w", **profile) as destination:
                destination.write(vv_source.read(1), 1)
                destination.write(vh_source.read(1), 2)
                destination.update_tags(PRODUCT_TYPE="GRD")
        yield (f"{pair['vv']} | {pair['vh']}", stacked)


def _sar_tile_id(path: Path, aoi_id: int, known_tile_ids: set[str]) -> str | None:
    with rasterio.open(path) as source:
        if source.crs is None:
            return None
        center_x = (source.bounds.left + source.bounds.right) / 2
        center_y = (source.bounds.bottom + source.bounds.top) / 2
        lon, lat = warp_transform(source.crs, "EPSG:4326", [center_x], [center_y])
    center_lon, center_lat = lon[0], lat[0]
    with db.get_conn() as conn:
        tiles = conn.execute(
            "SELECT tile_id, minlon, minlat, maxlon, maxlat FROM tiles WHERE aoi_id=? GROUP BY tile_id",
            (aoi_id,),
        ).fetchall()
    candidates = [row for row in tiles if row["tile_id"] in known_tile_ids]
    if not candidates:
        return None
    containing = [row for row in candidates if row["minlon"] <= center_lon <= row["maxlon"] and row["minlat"] <= center_lat <= row["maxlat"]]
    if containing:
        return containing[0]["tile_id"]
    minlon = min(row["minlon"] for row in candidates)
    maxlon = max(row["maxlon"] for row in candidates)
    minlat = min(row["minlat"] for row in candidates)
    maxlat = max(row["maxlat"] for row in candidates)
    if not (minlon <= center_lon <= maxlon and minlat <= center_lat <= maxlat):
        return None
    return min(candidates, key=lambda row: ((row["minlon"] + row["maxlon"]) / 2 - center_lon) ** 2 + ((row["minlat"] + row["maxlat"]) / 2 - center_lat) ** 2)["tile_id"]


def onboard_aoi_sar(aoi_name: str, sar_folder: str) -> SarOnboardReport:
    """Attach real Sentinel-1 rasters to the existing optical tile grid."""
    from app.geospatial.sar_features import compute_sar_features

    source_folder = Path(sar_folder)
    if not source_folder.exists():
        raise FileNotFoundError(f"SAR folder does not exist: {source_folder}")
    validate_remoteclip_config()
    db.init_db()
    aoi = db.get_aoi_by_name(aoi_name)
    if aoi is None:
        raise ValueError(f"AOI '{aoi_name}' must be onboarded optically before SAR data is attached")
    staging_dir = RAW_DIR / aoi_name / "sar_staging"
    for archive in sorted(source_folder.rglob("*.zip")):
        archive_dir = staging_dir / archive.stem
        archive_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as source_zip:
            root = archive_dir.resolve()
            for member in source_zip.infolist():
                destination = (archive_dir / member.filename).resolve()
                if root not in destination.parents and destination != root:
                    raise ValueError(f"Unsafe SAR zip member path: {member.filename}")
            source_zip.extractall(archive_dir)
    known_tile_ids = set(db.get_all_tile_ids(aoi["aoi_id"]))
    report = SarOnboardReport(aoi_id=aoi["aoi_id"], aoi_name=aoi_name)
    input_files = list(_sar_pairs(source_folder, staging_dir))
    if not input_files:
        raise ValueError(f"No paired VV/VH or two-band SAR rasters found in {source_folder}")

    for source_file, raster_path in input_files:
        outcome = SarOutcome(str(source_file), str(raster_path or ""), None, "failed")
        try:
            if raster_path is None:
                outcome.status = "skipped"
                outcome.error = "unsupported SAR input or missing matching VV/VH polarization"
                report.warnings.append(f"{source_file}: {outcome.error}")
                report.outcomes.append(outcome)
                continue
            metadata = infer_sar_metadata(raster_path)
            outcome.acquisition_date = metadata["date"]
            outcome.product_type = metadata["product_type"]
            tile_id = _sar_tile_id(raster_path, aoi["aoi_id"], known_tile_ids)
            if tile_id is None:
                outcome.status = "skipped"
                outcome.error = "SAR footprint center does not match a known optical tile_id for this AOI"
                report.warnings.append(f"{source_file}: {outcome.error}")
                report.outcomes.append(outcome)
                continue
            features = compute_sar_features(str(raster_path))
            db.register_sar_tile(
                tile_id=tile_id, tile_path=str(raster_path), features=features,
                product_type=metadata["product_type"], sensor="SENTINEL1", aoi_id=aoi["aoi_id"],
                period_start=metadata["period_start"], period_end=metadata["period_end"],
                acquisition_datetime=metadata["acquisition_datetime"],
                metadata={"source_files": str(source_file), "tags": metadata["tags"]},
            )
            outcome.status = "ingested"
            outcome.tile_id = tile_id
        except Exception as exc:
            outcome.error = str(exc)
            report.warnings.append(f"{source_file}: {exc}")
        report.outcomes.append(outcome)
    return report


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
    # Validate the embedding dependency before creating an AOI, extracting
    # scenes, or writing any catalog rows.
    validate_remoteclip_config()

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


def print_sar_onboard_report(report: SarOnboardReport):
    print(f"\n=== SAR onboarding report: '{report.aoi_name}' (aoi_id={report.aoi_id}) ===")
    print(f"SAR tiles ingested: {report.n_ingested} | skipped: {report.n_skipped} | failed: {report.n_failed}")
    for outcome in report.outcomes:
        line = f"  [{outcome.status:>8}] {outcome.acquisition_date or 'unknown'}  {outcome.source_file}"
        if outcome.tile_id:
            line += f"  tile={outcome.tile_id} product={outcome.product_type}"
        if outcome.error:
            line += f"  WARNING: {outcome.error}"
        print(line)
    for warning in report.warnings:
        print(f"  warning: {warning}")
