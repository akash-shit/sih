# Satellite Intelligence

Satellite Intelligence is an offline, geospatial change-detection and semantic search system for multi-temporal satellite imagery. It ingests Sentinel-2/Landsat scenes, tiles them into a consistent MGRS grid, computes spectral features (NDVI/NDWI/cloud/water coverage), embeds tiles with RemoteCLIP, stores metadata in SQLite, indexes vectors in FAISS, and then detects temporal change candidates for analyst review.

This project combines:
- a Python ingestion + detection pipeline under `app/`
- a FastAPI backend under `backend/`
- a React + Vite frontend under `frontend/`
- persistent local data and model storage in `data/` and `models/`

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

## Innovation Layer (v0.2)

Sentinel-1 support is an independent backscatter-delta branch for VV/VH GRD
and monthly mosaic products, not interferometric coherence. It preserves SAR
native resolution and uses physical tile correspondence for optional fusion;
real-data value-range and co-registration validation remains required.

Land-cover-aware scoring is a heuristic context classifier based on NDVI/NDWI,
and strategic priority uses analyst-configured AOI tiers, optional GeoJSON
zones, and proximity to confirmed hotspots. These signals reorder or explain
candidates; they never auto-confirm or hide analyst evidence.

The review queue exposes similarity feedback and an optional active-learning
reranker once enough confirm/reject decisions exist. Spectral difference
heatmaps use per-band percentile normalization and degrade to unavailable
when band metadata is ambiguous.

Per-AOI deterministic narratives remain the guaranteed explanation. An
optional local Llama 3.2 1B model through Ollama can produce a separate brief;
it is disabled by default, makes no remote calls, and falls back safely.

Useful commands include `python -m app.cli ingest-sar manifest.json`,
`python -m app.cli sar-stats`, and `python -m app.cli backfill-landcover`.

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

The application creates the following directories when it starts if they do not
already exist: `data/raw`, `data/tiles`, `data/index`, and `models`.

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

Other available CLI commands are `reingest`, `cluster`, `validate-remoteclip`,
`migrate-remoteclip`, `diagnose-source`, `add-aoi`, `inspect-zip`, `list-aois`,
`calibrate`, and `eval-report`. Run `python -m app.cli --help` for the complete
argument list.

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

The frontend defaults to `http://localhost:8000` through `VITE_API_BASE_URL`.
Set that variable before `npm run build` or `npm run dev` when the backend is
running elsewhere. The Vite development server listens on port `5173` and is
configured to accept connections from the local network.

To build the frontend for FastAPI to serve from `/`, run:

```bash
cd frontend
npm run build
```

Then restart FastAPI. When `frontend/dist` exists, the backend serves the built
frontend at `/` and generated imagery at `/generated/`.

## Docker

The image builds the frontend first, then runs the FastAPI backend and serves the
compiled UI from the same container. There is no separate frontend service.

Before starting the container, place the checkpoint at
`models/RemoteCLIP-ViT-B-32.pt`. The Compose file mounts `data/` read-write so
the SQLite catalog, generated imagery, tiles, and FAISS index persist on the
host, and mounts `models/` read-only.

```bash
docker compose build
docker compose up
```

Open `http://localhost:8000`. To run in the background, use
`docker compose up -d`; stop it with `docker compose down`. The API remains
available under the same origin, including `/docs`, `/stats`, and the frontend
routes. To use another checkpoint location or CORS policy, override
`REMOTECLIP_CHECKPOINT_PATH` or `CORS_ALLOWED_ORIGINS` in Compose.

## Detailed project workflow

For a step-by-step explanation of the full processing pipeline, see [PROJECT_WORKFLOW.md](PROJECT_WORKFLOW.md).

## Notes

- The project is intentionally local-first and offline-capable.
- The database stores provenance so results can be traced back to scene metadata and analyst decisions.
- The FAISS index is updated incrementally rather than rebuilt from scratch for each scene.
- The change detector combines machine-vision similarity with NDVI-driven spectral evidence and suppresses obvious false positives such as cloud, snow, and water-only seasonal variation.
