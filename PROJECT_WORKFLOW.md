# Project Workflow and Technical Architecture

This document explains how the Satellite Intelligence system works end to end, from raw satellite imagery to change candidates, semantic search, and review queue operations.

The current runtime has three code layers: the `app/` Python pipeline, the
`backend/` FastAPI integration layer, and the `frontend/` React/Vite client.
For production-style local use, the frontend is compiled into `frontend/dist`
and served by FastAPI from the same process. Docker packages those three layers
into one CPU container; `data/` and `models/` remain external mounted storage.

## 1. High-level system flow

```text
Raw GeoTIFF / Copernicus zip
        ↓
Scene validation and metadata extraction
        ↓
Tile generation on MGRS grid
        ↓
Spectral feature computation
        ↓
SQLite metadata registration
        ↓
CLIP embedding generation
        ↓
FAISS index append
        ↓
Temporal pairing across dates
        ↓
Hybrid scoring + false-positive suppression
        ↓
Candidate persistence
        ↓
Change classification / clustering / review queue
        ↓
Search and analyst verification
```

## 2. Source data and preprocessing

### 2.1 Supported raw inputs
The project accepts:
- GeoTIFF / COG files stored in `data/raw/`
- monthly Copernicus exports packaged as zip files
- AOI folders containing a group of scenes or zips

The primary spatial assumption is that the data is Sentinel-2-style multispectral imagery with bands such as:
- B02 (blue)
- B03 (green)
- B04 (red)
- B08 (NIR)
- SCL (scene classification layer)

### 2.2 Scene inspection
The first stage is implemented in `app/geospatial/reader.py`.

`inspect_scene(scene_path)` loads a raster and records:
- width and height
- CRS
- geotransform
- resolution
- band count
- nodata value
- raster dtype
- file tags

This is the validation gate that prevents broken or un-georeferenced files from entering the pipeline.

### 2.3 Validation logic
Before ingesting a scene, the pipeline ensures that:
- the file exists
- the CRS is known
- the raster has usable multispectral pixels
- the data is nonzero and valid

The ingestion orchestrator in `app/pipeline/ingest.py` calls these checks before tiles are generated.

## 3. Tiling and spatial normalization

### 3.1 Tile generation
The tiling logic is in `app/geospatial/tiler.py`.

It reads each scene in fixed-size windows (default `224 x 224` pixels), writes each tile as a GeoTIFF, and generates a stable MGRS-based identifier for every tile.

Each tile object contains:
- `tile_id`
- `scene_path`
- `tile_path`
- `row` and `col`
- WGS84 bounding box
- `acquisition_date`
- `sensor`

### 3.2 Why the MGRS tile ID matters
The tile ID is used as a stable spatial anchor across time. If the same ground cell is observed in multiple scenes, the system can compare them as the same spatial unit even when acquisition dates differ.

This is essential for temporal change detection because the system is not comparing random scene patches; it is comparing the same ground footprint over time.

## 4. Spectral feature extraction

The spectral feature layer in `app/geospatial/features.py` computes per-tile metrics:
- NDVI mean
- NDVI standard deviation
- NDWI mean
- cloud fraction
- snow fraction
- water fraction
- valid pixel fraction

These metrics are not just metadata; they are used later to:
- detect vegetation/land cover change
- filter obviously bad observations
- suppress false positives from cloud or water seasonality

### 4.1 NDVI and NDWI
The system uses standard formulations:
- NDVI = (NIR - RED) / (NIR + RED)
- NDWI = (GREEN - NIR) / (GREEN + NIR)

These provide a physically grounded signal beyond pure visual embedding similarity.

## 5. SQLite metadata and provenance store

The database layer is defined in `app/geospatial/catalog_db.py`.

It stores:
- AOI metadata
- scenes metadata
- tiles metadata
- change candidates
- audit log entries
- analyst decisions

Key tables include:
- `aois`
- `scenes`
- `tiles`
- `change_candidates`
- `audit_log`

This database is the system of record for provenance. It answers questions like:
- which scenes belong to which AOI?
- which tiles came from which scene?
- what were the dates and metadata?
- which candidate was confirmed or rejected?

## 6. Embedding and vector search

### 6.1 Embedding layer
The embedding logic in `app/embeddings/clip_embedder.py` transforms each tile into a fixed-length vector using the locally staged RemoteCLIP checkpoint through OpenCLIP's model implementation.

The system does this in batches to avoid repeated per-image overhead.

### 6.2 Vector index
The FAISS wrapper is implemented in `app/index/vector_index.py`.

Important properties of the index:
- vectors are stored with integer IDs aligned to `tiles.vector_id`
- new vectors are appended incrementally
- the index is saved to disk and can be reused
- re-ingestion does not rebuild the whole index from scratch

This makes the system suitable for showing “incremental ingestion” rather than a full reindex on every add.

### 6.3 Search
The semantic search logic in `app/index/search.py` queries the FAISS index using text or image similarity and returns the nearest matching tiles.

This supports:
- text-to-image search
- geographic similarity retrieval
- feature discovery through embedding space

## 7. Ingestion orchestration

The end-to-end ingestion flow is centralized in `app/pipeline/ingest.py`.

The orchestration order is:
1. check if the scene is already ingested
2. validate the scene file
3. register the scene in SQLite
4. tile the scene into fixed geographic windows
5. compute tile features
6. write tile metadata to SQLite
7. embed tiles in a batch
8. append vectors to FAISS
9. update AOI extent if applicable

This is the pipeline’s central contract, and the CLI and API call into it rather than re-implementing it elsewhere.

## 8. Temporal change detection

The change detection layer is implemented in `app/change/detector.py`.

The flow is:
1. fetch the tile history for one spatial cell (`tile_id`)
2. iterate each consecutive observation pair
3. compare their embedding vectors
4. compute a spectral delta from NDVI difference
5. combine both into a hybrid score
6. run false-positive suppression rules
7. insert the result into `change_candidates`

### 8.1 Hybrid scoring
Each compare produces:
- `embedding_drift`: how different the CLIP embeddings are
- `spectral_delta`: difference in NDVI
- `combined_score`: weighted combination of image drift and spectral evidence

The logic is intentionally designed so that pure embedding mismatch alone is not enough to become a candidate.

### 8.2 False-alarm suppression
The detector applies quality gates in `app/change/detector.py`:
- too much cloud cover
- too few valid pixels
- high snow cover
- strong seasonal water variation that is explainable by NDWI movement

If a pair fails these checks, it is suppressed and not pushed to review as a real change candidate.

## 9. Candidate persistence and review queue

Once a candidate is generated, it is stored in SQLite as a `change_candidate` record.

The review queue is assembled by `app/review/queue.py`.

The queue includes:
- candidate ID
- before/after dates
- score values
- classification labels
- result of analyst decisions

Analyst decisions are logged to `audit_log`, which gives full traceability for each confirmed or rejected suggestion.

### 9.1 Human-in-the-loop reranking
When an analyst confirms a candidate, the review layer boosts similar, still-open candidates in the same embedding neighborhood. This does not auto-confirm a result; it simply changes the shortlist ordering to help analysts focus on likely real changes faster.

## 10. Discovery and clustering

The clustering logic in `app/discovery/clustering.py` groups tiles into similar visual regions using HDBSCAN with a KMeans fallback for small datasets.

The main purpose is to answer: “Given one location of interest, what other tiles or regions look similar?”

This helps the user:
- discover similar sites
- cluster nearby patterns by visual semantics
- group change hotspots across AOIs

## 11. Change classification

The classifier in `app/change/classifier.py` assigns a label such as a change type to a candidate once it survives the quality gate.

This is a zero-shot or heuristic classification step based on the tile image and its spectral context, not a learned classification model stored in the repo.

## 12. AOI onboarding workflow

The AOI onboarding pipeline in `app/pipeline/onboard_aoi.py` allows an entire folder of scenes or Copernicus exports to be processed as a single region.

The full onboarding flow:
1. read every zip or TIFF in the folder
2. parse acquisition date and cloud metadata from extraction JSON
3. validate batch consistency across scenes
4. identify duplicates or missing months
5. register AOI metadata
6. call the normal ingestion pipeline per scene
7. update the AOI extent and all derived metadata

This is how a real region like Dholera or Navi Mumbai can be ingested in bulk rather than one scene at a time.

## 13. API layer

The FastAPI app in `backend/main.py` exposes the same internal functionality to the frontend.

It wraps the logic for:
- AOI listing and stats
- search queries
- review queue access
- analyst decisions
- tile and cluster retrieval
- generated thumbnails and difference images

This keeps the business logic in `app/` while making the API a thin integration layer.

The implemented API groups are:
- `/stats` for catalog and processing counts
- `/aois` and `/aois/{aoi_id}/timeline` for AOI browsing
- `/search/text` and `/search/image` for semantic retrieval
- `/tiles/...` and `/vectors/...` for tile details, similarity, and comparison
- `/changes/...` and `/review/...` for candidates, evidence, decisions, and audit history
- `/clusters/...` for discovery results
- `/aois/onboard` for background AOI ingestion jobs
- `/generated/...` for generated thumbnails, mosaics, and difference images

Interactive API documentation is available at `/docs` when the backend is running.

## Innovation Layer (v0.2) architecture

The SAR branch stores Sentinel-1 VV/VH observations in the dedicated
`sar_tiles` table and computes native-resolution backscatter-delta features.
Optical and SAR evidence are matched at the stable physical tile footprint;
monthly mosaics retain period metadata and do not receive fabricated exact
acquisition timestamps. Temporal signatures and velocity compare the
resulting candidate scores over time, while preserving score provenance.

Candidate review ordering can additionally use land-cover context, strategic
AOI priority, similarity feedback, and a trained analyst active-learning
probability. Priority and learned scores are ranking signals only. Spectral
difference heatmaps and deterministic narratives are explanatory outputs, and
the optional local Ollama Llama 3.2 1B brief is post-processing only.

SAR CLI ingestion is raster-first: `ingest-sar` reads VV/VH bands, runs
`compute_sar_features` on the source raster, and registers the result through
`register_sar_tile` in `sar_tiles`. Product type and acquisition/period
metadata may be supplied with flags or inferred from GeoTIFF tags (and the
filename for monthly mosaics). The former JSON `sar_observations` path is
retained only for API compatibility and is not used for fusion or CLI stats.
The review queue displays a strategic-priority badge when a priority score is
available: high (>=0.75), medium (>=0.45), or low. `app/change/reranker.py`
is a legacy offline compatibility helper; production learned ordering lives
in `app/review/queue.py`.

## 14. Frontend flow

The frontend in `frontend/` is a React + Vite app that connects to the backend.
During development, run Vite on port `5173` and point `VITE_API_BASE_URL` at the
FastAPI server. For a packaged run, `npm run build` writes `frontend/dist` and
FastAPI serves that directory at `/`.

Typical UI actions include:
- choose or inspect AOIs
- view scene timeline data
- run semantic search
- review candidate changes
- inspect clusters and similar sites
- view generated difference thumbnails

## 15. End-to-end runtime behavior

A typical operational cycle looks like this:

```bash
python -m app.cli ingest scene1.tif 2025-01-15 SENTINEL2
python -m app.cli ingest scene2.tif 2025-06-10 SENTINEL2
python -m app.cli detect-changes --threshold 0.22 --classify
python -m app.cli cluster
python -m app.cli review-queue
python -m app.cli decide 5 confirm --reason "matches known construction permit"
python -m app.cli search-text "newly built structures near a river"
python -m app.cli stats
```

This process creates a living record of indexed scenes, feature vectors, change candidates, and analyst decisions.

## 16. Container runtime

`Dockerfile` uses a two-stage build:
1. Node 22 installs the locked frontend dependencies and creates the Vite build.
2. Python 3.12 installs the geospatial/ML/API dependencies, copies the pipeline
        and backend, and serves the compiled frontend with Uvicorn on port `8000`.

`docker-compose.yml` runs that image as the `backend` service. It mounts:
- `./data:/app/data` read-write for the SQLite catalog, raw scenes, tiles,
  generated images, and FAISS assets
- `./models:/app/models:ro` for the local RemoteCLIP checkpoint

The container sets `SATSEARCH_CLIP_DEVICE=cpu` and does not download model
weights. Start it with `docker compose up --build` and open `http://localhost:8000`.
The development frontend remains available separately at `http://localhost:5173`.

## 17. Design principles

The project is intentionally built around a few key principles:

- offline-first: no cloud service is required at inference time
- provenance-first: metadata is always kept in SQLite
- append-only vector indexing: new scenes extend the index rather than replacing it
- explainable detection: hybrid scoring combines image and spectral evidence
- analyst-in-the-loop: humans confirm or reject candidates and affect ranking

## 18. Summary

The project is a complete local-first pipeline for satellite change analysis: it ingests imagery, extracts geospatial features, embeds each tile with CLIP, detects meaningful change over time, suppresses false positives, clusters similar patterns, and exposes everything through a searchable review workflow.

The codebase intentionally separates the core scientific pipeline (`app/`) from the API (`backend/`) and the UI (`frontend/`), making it easier to evolve the system without rewriting the underlying logic.
