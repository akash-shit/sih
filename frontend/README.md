# Satellite Intelligence — Backend Automation (SIH 26227)

Semantic retrieval + multi-temporal change analysis over satellite
imagery. This repo is **backend automation only**, deliberately, per
the current build phase: prove the pipeline works and is testable
before any FastAPI or website layer is introduced.

No LLM anywhere in this repo. No cloud calls. Everything below runs
fully offline once dependencies and the embedding model weights are
staged locally.

## What's implemented (maps to the 19-stage architecture doc)

| Stage | Module |
|---|---|
| 2. GeoTIFF/COG reading | `app/geospatial/reader.py` |
| 3–4. Tiling + MGRS grid + normalization | `app/geospatial/tiler.py` |
| 5. NDVI/NDWI/quality features | `app/geospatial/features.py` |
| 6. Metadata + provenance (SQLite) | `app/geospatial/catalog_db.py` |
| — | Copernicus zip metadata extraction (real sensing date/cloud%) | `app/geospatial/copernicus_metadata.py` |
| — | pre-ingestion batch validation (CRS/shape/band/date-gap checks) | `app/pipeline/batch_validate.py` |
| — | one-call AOI onboarding from a folder of zips/tifs | `app/pipeline/onboard_aoi.py` |
| 7. CLIP embedding generation | `app/embeddings/clip_embedder.py` |
| 8/18. FAISS index + incremental add | `app/index/vector_index.py` |
| — | orchestrator tying 2→8 together: `app/pipeline/ingest.py` |
| 9/10. Text + image search | `app/index/search.py` |
| 11/12/13/15. Temporal pairing, hybrid scoring, suppression, earliest-date | `app/change/detector.py` |
| 14. Zero-shot change-type classification | `app/change/classifier.py` |
| 16. Clustering / discovery | `app/discovery/clustering.py` |
| 17. Review queue, audit trail, reranking | `app/review/queue.py` |
| — | per-cluster threshold calibration | `app/change/calibration.py` |
| — | CLI entry point for all of the above | `app/cli.py` |

The FastAPI integration lives in `backend/` and calls the modules above
directly. It does not duplicate ingestion, search, change detection, or
review logic.

## Run the integrated application

Install the backend dependencies and start the API:

```bash
python -m pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

For frontend development, in another terminal:

```bash
cd src
npm install
npm run dev
```

The frontend uses `VITE_API_BASE_URL=http://localhost:8000` and
`VITE_USE_FIXTURES=false` for the real pipeline. To serve a built frontend
from the same FastAPI process, run `npm run build` in `src/`; the API exposes
that build at `/`.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Stage the official OpenCLIP-format `RemoteCLIP-ViT-B-32.pt` checkpoint at
`models/RemoteCLIP-ViT-B-32.pt`, or set `REMOTECLIP_CHECKPOINT_PATH` to an
existing local copy. The application fails clearly when it is absent and
never downloads model weights at runtime.

## Getting real imagery

### Adding a new AOI (Dholera, or any other region) -- the automatic way

If you've downloaded Copernicus Browser exports as .zip files (one per month, each containing the GeoTIFF plus request/metadata JSON), point the onboarding pipeline straight at the folder:

```bash
python -m app.cli add-aoi dholera path/to/dholera_zips_folder
```

This one command:
1. Extracts every `.zip` (or picks up already-extracted `.tif`/`.tiff` files directly -- mixing both in one folder is fine).
2. Pulls the **real** acquisition date and cloud-cover percentage out of each zip's metadata JSON (not the filename) -- see `app/geospatial/copernicus_metadata.py`. It records which strategy found the date (`json_metadata` / `json_timerange_fallback` / `geotiff_tag` / `filename`) so a less-reliable fallback is visible, not silently trusted.
3. Validates the whole batch **before** ingesting anything: checks every scene shares the same CRS, the same pixel dimensions, and the same band count, flags duplicate dates, flags months with no scene at all in the covered range, and summarizes cloud cover per month. A bad month is reported and skipped individually -- it never blocks the other good months.
4. Registers the AOI (name + bounding box + date range, auto-computed from what got ingested) in a new `aois` table.
5. Runs every valid scene through the exact same tested pipeline a single scene goes through (tiling → NDVI/NDWI → embedding → FAISS indexing), tagged with the new `aoi_id`.
6. Prints a full report: how many scenes were ingested/failed, how many tiles were added, and every validation warning found.

Two helper commands:
```bash
python -m app.cli inspect-zip path/to/one_month.zip   # see exactly what's inside a real zip before trusting the parser on the whole batch
python -m app.cli list-aois                            # see every onboarded AOI and its computed extent
```

**Important first step with real data:** before running `add-aoi` on your full ~72-zip batch per location, run `inspect-zip` on ONE real Dholera zip and check the printed JSON. `copernicus_metadata.py`'s key-name lists (`_DATE_KEYS`, `_CLOUD_KEYS`, `_PRODUCT_KEYS`) cover the common Sentinel Hub/Copernicus metadata key names, but if your export's JSON uses different key names, add them there -- the parser recurses through the whole JSON structure looking for a case-insensitive match, so most real-world variants just need the key name added, not new code.

### If you don't have real zips yet -- synthetic fixtures

Two generators exist purely for testing the pipeline without real data:
```bash
python3 -m tests.make_synthetic_scenes            # single-AOI, no metadata (original smoke test)
python3 -m tests.make_synthetic_copernicus_zips    # a folder of fake Copernicus-style zips, for testing add-aoi end to end
```

### Real data sources

Primary real sources (per the PS's own dataset section): Copernicus
Sentinel-2 (via the Copernicus Data Space Ecosystem / Copernicus Browser),
USGS Landsat Collection 2, NRSC/ISRO Bhuvan. BigEarthNet pre-cut patches are
a good fallback if live download access is unreliable on hackathon Wi-Fi.

Band convention assumed throughout: 1=B02, 2=B03, 3=B04, 4=B08, 5=SCL. When
downloading from Copernicus Browser, make sure "Clip extra bands" is on and
the band list is in that order for every month -- `add-aoi`'s validation
step will catch a band-count mismatch, but it can't catch a silently
reordered band list, since that just looks like a valid 5-band file.

## Running the pipeline end to end

```bash
# 1. Ingest every scene you have (repeatable/idempotent — re-running on
#    an already-ingested scene is a safe no-op)
python -m app.cli ingest data/raw/aoi_2025-01-15.tif 2025-01-15 SENTINEL2
python -m app.cli ingest data/raw/aoi_2025-06-10.tif 2025-06-10 SENTINEL2

# 2. Build discovery clusters (needed before per-cluster calibration,
#    and what powers "find similar sites")
python -m app.cli cluster

# 3. Run change detection + zero-shot change-type classification
python -m app.cli detect-changes --threshold 0.22 --classify

# 4. See what needs analyst review
python -m app.cli review-queue

# 5. Confirm or reject a candidate (this also nudges reranking of
#    similar open candidates)
python -m app.cli decide 5 confirm --reason "matches known construction permit"

# 6. Try semantic search
python -m app.cli search-text "newly built structures near a river"

# 7. Numbers for the evaluation report
python -m app.cli stats
```

### Incremental ingestion, proven

```bash
python -m app.cli stats                      # note faiss_ntotal
python -m app.cli ingest data/raw/aoi_2025-07-02.tif 2025-07-02 SENTINEL2
python -m app.cli stats                      # faiss_ntotal grew, nothing rebuilt
```

`VectorIndex.add_vectors()` (in `app/index/vector_index.py`) always
appends to the existing FAISS structure on disk — there is no code
path that discards and rebuilds it. That is the direct, checkable
answer to the "incremental ingestion, no full rebuild" requirement.

### Testing false-alarm suppression directly

The synthetic cloud patch in the generator may or may not exceed your
configured `MAX_CLOUD_FRACTION` (see `app/config.py`) depending on how
large you make it relative to tile size — that's intentional, so you
learn to tune the threshold against your real AOI's typical cloud
patch size rather than trusting a hard-coded number. To confirm the
suppression *logic* itself is correct independent of any specific
scene, call it directly:

```python
from app.change.detector import _quality_gate
before = {"cloud_fraction": 0.02, "valid_pixel_fraction": 1.0, "snow_fraction": 0.0, "ndwi_mean": 0.0, "ndvi_mean": 0.3}
after  = {"cloud_fraction": 0.40, "valid_pixel_fraction": 1.0, "snow_fraction": 0.0, "ndwi_mean": 0.0, "ndvi_mean": 0.31}
print(_quality_gate(before, after))   # -> "cloud_fraction_too_high_after=0.40"
```

## RemoteCLIP checkpoint

Everything downstream talks to `app/embeddings/clip_embedder.py`'s four
functions (`embed_image_tile`, `embed_image_tiles_batch`, `embed_text`,
`embed_texts_batch`) — nothing else imports `open_clip` directly. To
switch backbones:

1. Stage `RemoteCLIP-ViT-B-32.pt` under the project-level `models/` directory.
2. Run `python -m app.cli validate-remoteclip` with the root `.venv` active.
3. If an existing index was created by another model, perform a controlled
   real-tile re-embedding migration before searching; embeddings from two
   different backbones are not comparable in the same index.

## Project layout

```
satellite-intelligence/
├── app/
│   ├── config.py
│   ├── cli.py
│   ├── geospatial/   (reader, tiler, features, catalog_db, copernicus_metadata)
│   ├── embeddings/   (clip_embedder)
│   ├── index/        (vector_index, search)
│   ├── change/       (detector, classifier, calibration)
│   ├── discovery/    (clustering)
│   ├── pipeline/     (ingest, batch_validate, onboard_aoi)
│   └── review/       (queue)
├── data/
│   ├── raw/          (input GeoTIFF/COG scenes, one subfolder per AOI)
│   ├── tiles/         (per-tile GeoTIFFs written by the tiler)
│   ├── index/         (tiles.faiss)
│   └── catalog.sqlite
├── tests/
│   ├── make_synthetic_scenes.py
│   └── make_synthetic_copernicus_zips.py
├── requirements.txt
└── README.md
```

## What comes next (not in this repo yet)

Once you're satisfied the automation above is correct on real Sentinel-2
data: wrap these same functions behind FastAPI endpoints
(`POST /search/text`, `POST /search/image`, `POST /change/analyze`,
`GET /tiles/{id}`, `GET /clusters/{id}`, `POST /review`, `POST /ingest`
— see the architecture doc's section 10), then build the React frontend
against that API contract using the local React/Vite frontend.
for that stage when you're ready — they're intentionally not included
here so this phase stays focused on the pipeline itself.
