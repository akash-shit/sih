"""
Copernicus Browser export parsing.

Copernicus Browser's "Analytical" download packages a zip per request
containing the GeoTIFF plus (depending on which download options were
ticked) a request.json describing the request that was sent, and --
if "Show metadata" / tile-info options were enabled -- extra JSON with
the actual sensing time and cloud coverage of the product that was
returned. Exact filenames and JSON shape vary by download option and
have changed across Browser versions, so this module does NOT assume
one fixed schema. Instead it:

  1. Extracts the zip.
  2. Finds the raster file (.tif/.tiff).
  3. Recursively scans every .json file in the zip for a set of known
     key names (case-insensitive) that commonly carry sensing date and
     cloud cover, wherever they appear in the JSON structure.
  4. Falls back, in order, to: request.json's time range -> the
     GeoTIFF's own embedded tags -> a date pattern in the filename.
  5. Always records WHICH strategy produced the date
     (acquisition_date_source), so a less-reliable fallback is visible
     in provenance rather than silently treated as certain.

IMPORTANT: the key names in _DATE_KEYS / _CLOUD_KEYS / _PRODUCT_KEYS
below are the common ones Copernicus/Sentinel Hub metadata uses, but
zip contents vary. The first time you run this against your real
Dholera export, call `inspect_zip()` on one zip and eyeball what keys
actually show up -- add any you find missing to the lists below.
"""
import json
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import rasterio

# Known key names (checked case-insensitively) that commonly hold the
# real acquisition/sensing timestamp in Sentinel Hub / Copernicus
# Browser metadata JSON, roughly in order of how trustworthy they are.
_DATE_KEYS = [
    "sensingtime", "sensing_time", "datetime", "acquisitiondate",
    "acquisition_date", "date", "timestamp", "from",
]
_CLOUD_KEYS = [
    "cloudcoverpercentage", "cloud_cover_percentage", "cloudcover",
    "cloud_cover", "cloudcoverage",
]
_PRODUCT_KEYS = [
    "productid", "product_id", "tileid", "tile_id", "id",
]

_FILENAME_DATE_RE = re.compile(r"(20\d{2})[-_]?(\d{2})(?:[-_]?(\d{2}))?")


@dataclass
class SceneMetadata:
    acquisition_date: str                 # normalized YYYY-MM-DD
    acquisition_date_source: str          # json_metadata | json_timerange_fallback | geotiff_tag | filename
    cloud_cover_percent: Optional[float]
    product_id: Optional[str]
    raw_metadata: dict = field(default_factory=dict)   # everything we found, for provenance storage


def _walk_json_for_keys(obj, wanted_keys: list[str], found: dict):
    """Recursively walk an arbitrary JSON structure and collect the
    first value seen for each wanted key (case-insensitive match on
    key name), regardless of how deeply it's nested."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            lk = k.lower().replace(" ", "")
            if lk in wanted_keys and lk not in found:
                found[lk] = v
            _walk_json_for_keys(v, wanted_keys, found)
    elif isinstance(obj, list):
        for item in obj:
            _walk_json_for_keys(item, wanted_keys, found)


def _normalize_date(raw_value) -> Optional[str]:
    """Accepts an ISO datetime, a date string, or a unix timestamp and
    returns YYYY-MM-DD, or None if it can't be parsed."""
    if raw_value is None:
        return None
    if isinstance(raw_value, (int, float)):
        try:
            return datetime.utcfromtimestamp(raw_value).strftime("%Y-%m-%d")
        except (ValueError, OSError):
            return None
    s = str(raw_value).strip()
    # Try a handful of common formats before giving up.
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:len(fmt) + 4], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Last resort: pull YYYY-MM(-DD) out of whatever string we have.
    m = _FILENAME_DATE_RE.search(s)
    if m:
        year, month, day = m.group(1), m.group(2), m.group(3) or "01"
        return f"{year}-{month}-{day}"
    return None


def inspect_zip(zip_path: str) -> dict:
    """Debug helper -- run this once against a real Copernicus export
    to see exactly what's inside before trusting the automatic parser
    on your full batch. Prints nothing; returns a dict you can print
    or json.dumps yourself."""
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        json_contents = {}
        for name in names:
            if name.lower().endswith(".json"):
                try:
                    json_contents[name] = json.loads(zf.read(name))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    json_contents[name] = "<unparsable>"
    return {"files": names, "json_contents": json_contents}


def extract_zip_to_scene(zip_path: str, staging_dir: str) -> tuple[str, SceneMetadata]:
    """Extracts one Copernicus Browser zip and returns
    (path_to_extracted_tif, SceneMetadata). staging_dir is where the
    raw files land -- pass a per-AOI subfolder so batches don't collide."""
    zip_path = Path(zip_path)
    staging_dir = Path(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        tif_names = [n for n in names if n.lower().endswith((".tif", ".tiff"))]
        if not tif_names:
            raise ValueError(f"No .tif/.tiff found inside {zip_path}")
        tif_name = tif_names[0]  # Copernicus Browser analytical exports are one raster per zip

        extract_target = staging_dir / f"{zip_path.stem}.tif"
        with zf.open(tif_name) as src, open(extract_target, "wb") as dst:
            dst.write(src.read())

        # Gather every JSON file's content for key-scanning + full provenance.
        all_json = {}
        for name in names:
            if name.lower().endswith(".json"):
                try:
                    all_json[name] = json.loads(zf.read(name))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

    date_found, cloud_found, product_found = {}, {}, {}
    for content in all_json.values():
        _walk_json_for_keys(content, _DATE_KEYS, date_found)
        _walk_json_for_keys(content, _CLOUD_KEYS, cloud_found)
        _walk_json_for_keys(content, _PRODUCT_KEYS, product_found)

    acquisition_date, source = None, None

    # Strategy 1: a real sensing-time-like key found anywhere in the metadata JSON.
    for key in _DATE_KEYS:
        if key in date_found:
            normalized = _normalize_date(date_found[key])
            if normalized:
                acquisition_date, source = normalized, "json_metadata"
                break

    # Strategy 2: request.json's requested time range (less precise --
    # it's the window given to the API, not necessarily the exact
    # sensing moment of the product actually returned).
    if acquisition_date is None:
        for name, content in all_json.items():
            if "request" in name.lower():
                found = {}
                _walk_json_for_keys(content, ["from", "to"], found)
                candidate = found.get("to") or found.get("from")
                normalized = _normalize_date(candidate)
                if normalized:
                    acquisition_date, source = normalized, "json_timerange_fallback"
                    break

    # Strategy 3: whatever date tag the GeoTIFF itself carries.
    if acquisition_date is None:
        try:
            with rasterio.open(extract_target) as src:
                tags = src.tags()
            for k, v in tags.items():
                if "date" in k.lower() or "time" in k.lower():
                    normalized = _normalize_date(v)
                    if normalized:
                        acquisition_date, source = normalized, "geotiff_tag"
                        break
        except rasterio.errors.RasterioIOError:
            pass

    # Strategy 4: last resort, a date pattern in the zip's own filename.
    if acquisition_date is None:
        normalized = _normalize_date(zip_path.stem)
        if normalized:
            acquisition_date, source = normalized, "filename"

    if acquisition_date is None:
        raise ValueError(
            f"Could not determine acquisition date for {zip_path} by any strategy -- "
            f"run inspect_zip() on it and add the real key name to _DATE_KEYS."
        )

    cloud_cover = None
    for key in _CLOUD_KEYS:
        if key in cloud_found:
            try:
                cloud_cover = float(cloud_found[key])
            except (TypeError, ValueError):
                pass
            break

    product_id = None
    for key in _PRODUCT_KEYS:
        if key in product_found:
            product_id = str(product_found[key])
            break

    metadata = SceneMetadata(
        acquisition_date=acquisition_date,
        acquisition_date_source=source,
        cloud_cover_percent=cloud_cover,
        product_id=product_id,
        raw_metadata={"source_zip": str(zip_path), "json_files": all_json},
    )
    return str(extract_target), metadata
