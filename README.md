# Satellite Intelligence

Satellite Intelligence is an offline, geospatial change-detection and semantic search system for multi-temporal satellite imagery. It ingests Sentinel-2/Landsat scenes, tiles them into a consistent MGRS grid, computes spectral features (NDVI/NDWI/cloud/water coverage), embeds tiles with RemoteCLIP, stores metadata in SQLite, indexes vectors in FAISS, and then detects temporal change candidates for analyst review.

This project combines:
- a Python ingestion + detection pipeline under `app/`
- a FastAPI backend under `backend/`
- a React + Vite frontend under `frontend/`
- local data storage in `data/`

It is designed to work fully offline once the RemoteCLIP checkpoint is staged locally.

## What the system does

1. Reads raw GeoTIFF/COG scenes and validates them before processing.
2. Splits scenes into fixed-size tiles on a shared spatial grid.
3. Computes per-tile spectral quality and vegetation metrics.
4. Stores scene/tile provenance in SQLite.
5. Generates CLIP embeddings for every tile.
6. Builds and updates a FAISS vector index incrementally.
7. Compares consecutive observations for each ground cell.
8. Suppresses false positives using cloud/valid-pixel/snow/water checks.
9. Promotes real change candidates to an analyst review queue.
10. Supports semantic text search and cluster-based “similar site” discovery.
11. Exposes the pipeline through both CLI commands and an API layer.

## Core project structure

```text
satellite-intelligence/
├── app/
│   ├── cli.py                     # main CLI entry point
│   ├── config.py                 # central config and filesystem paths
│   ├── geospatial/
│   │   ├── reader.py             # scene metadata / CRS validation
│   │   ├── tiler.py              # tile generation and MGRS IDs
│   │   ├── features.py           # NDVI/NDWI/cloud/snow metrics
│   │   ├── catalog_db.py         # SQLite schema and data access
│   │   ├── copernicus_metadata.py# zip metadata parsing
│   │   └── rendering.py          # rendering helpers for UI previews
│   ├── embeddings/
│   │   └── clip_embedder.py      # RemoteCLIP embedding logic
│   ├── index/
│   │   ├── vector_index.py       # FAISS append-only index wrapper
│   │   └── search.py             # semantic search
│   ├── change/
│   │   ├── detector.py           # temporal pairing / hybrid scoring
│   │   ├── classifier.py         # change-type classification
│   │   └── calibration.py        # calibration helpers
│   ├── discovery/
│   │   └── clustering.py         # HDBSCAN/KMeans discovery
│   ├── pipeline/
│   │   ├── ingest.py             # ingestion orchestrator
│   │   ├── batch_validate.py     # batch validation logic
│   │   └── onboard_aoi.py        # AOI onboarding from zip/tif folders
│   └── review/
│       └── queue.py              # review queue and analyst feedback
├── backend/
│   ├── main.py                   # FastAPI app and endpoints
│   └── rendering.py              # image generation helpers for API responses
├── frontend/
│   ├── package.json              # Vite/React app config
│   ├── src/                     # frontend source code
│   └── public/                  # static assets
├── data/
│   ├── raw/                     # source scenes
│   ├── tiles/                   # generated per-tile TIFFs
│   ├── index/                   # FAISS assets
│   ├── generated/               # rendered thumbnails / differences
│   └── catalog.sqlite           # metadata database
├── requirements.txt
├── README.md
├── PROJECT_WORKFLOW.md          # detailed technical workflow
└── ...
```

## Tech stack

- Python 3
- rasterio for geospatial reading/writing
- mgrs for stable tile IDs
- numpy + pillow for array/image handling
- RemoteCLIP via OpenCLIP + torch for local embeddings
- FAISS for vector search and nearest-neighbor retrieval
- SQLite for metadata, provenance, and AOI tracking
- scikit-learn + hdbscan for discovery and grouping
- FastAPI for backend APIs
- React + Vite for the UI

## Setup

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

Stage the official OpenCLIP-format `RemoteCLIP-ViT-B-32.pt` checkpoint at `models/RemoteCLIP-ViT-B-32.pt`, or set `REMOTECLIP_CHECKPOINT_PATH` to an existing local copy. The application fails clearly when it is absent and never downloads model weights at runtime.

## Quick start

### 1. Ingest a scene

```bash
python -m app.cli ingest data/raw/example_scene.tif 2025-01-15 SENTINEL2
```

### 2. Run change detection

```bash
python -m app.cli detect-changes --threshold 0.22 --classify
```

### 3. Review the queue

```bash
python -m app.cli review-queue
python -m app.cli decide 5 confirm --reason "matches known construction permit"
```

### 4. Run semantic search

```bash
python -m app.cli search-text "newly built structures near a river"
```

### 5. Inspect project stats

```bash
python -m app.cli stats
```

## AOI onboarding with real data

If you have Copernicus Browser exports or other raw monthly zip folders, onboard an AOI in one call:

```bash
python -m app.cli add-aoi dholera path/to/dholera_zips_folder
```

This command does the following:
- extracts zip contents or reads existing `.tif` files
- reads metadata from the exported JSON for acquisition date and cloud cover
- validates CRS, band layout, scene dimensions, duplicate dates, and month coverage
- creates or updates an AOI record
- ingests each valid scene through the normal pipeline
- reports warnings and ingestion counts

Useful helpers:

```bash
python -m app.cli inspect-zip path/to/one_month.zip
python -m app.cli list-aois
```

## Local backend + frontend

Start the backend:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the backend on `http://localhost:8000` and typically uses `VITE_API_BASE_URL=http://localhost:8000`.

To build and serve the frontend from the backend, run:

```bash
cd frontend
npm run build
```

Then the FastAPI app can expose the built frontend at `/`.

## Detailed project workflow

For a step-by-step explanation of the full processing pipeline, see [PROJECT_WORKFLOW.md](PROJECT_WORKFLOW.md).

## Notes

- The project is intentionally local-first and offline-capable.
- The database stores provenance so results can be traced back to scene metadata and analyst decisions.
- The FAISS index is updated incrementally rather than rebuilt from scratch for each scene.
- The change detector combines machine-vision similarity with NDVI-driven spectral evidence and suppresses obvious false positives such as cloud, snow, and water-only seasonal variation.
