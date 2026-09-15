"""
Central configuration for the Satellite Intelligence pipeline.
Every other module imports paths and constants from here so nothing
is hard-coded twice.
"""
import os
from pathlib import Path

# ---- Filesystem layout -----------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"
RAW_DIR = DATA_DIR / "raw"          # original GeoTIFF / COG scenes land here
TILES_DIR = DATA_DIR / "tiles"      # cropped, per-tile GeoTIFFs
INDEX_DIR = DATA_DIR / "index"      # FAISS index files
DB_PATH = DATA_DIR / "catalog.sqlite"

for d in (RAW_DIR, TILES_DIR, INDEX_DIR, MODELS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---- Tiling ------------------------------------------------------------
TILE_SIZE_PX = 224          # matches CLIP's native input size, no resize needed
TILE_GRID_ZONE_METERS = 2240  # 224 px * 10 m Sentinel-2 resolution -> tile footprint

# ---- Embedding model -----------------------------------------------------
# The project is explicitly required to use a local RemoteCLIP checkpoint.
# This is the official OpenCLIP-format filename for the ViT-B-32 variant.
REMOTECLIP_CHECKPOINT = Path(
    os.getenv(
        "REMOTECLIP_CHECKPOINT_PATH",
        str(MODELS_DIR / "RemoteCLIP-ViT-B-32.pt"),
    )
).expanduser().resolve()

CLIP_MODEL_NAME = "ViT-B-32"
EMBEDDING_DIM = 512
CLIP_DEVICE = os.getenv("SATSEARCH_CLIP_DEVICE", "cuda" if __import__("torch").cuda.is_available() else "cpu")
REMOTECLIP_ORIGIN = "Official RemoteCLIP release by ChenDelong1999; OpenCLIP-compatible checkpoint"
REMOTECLIP_LICENSE = "Apache-2.0 official repository license; verify checkpoint-specific terms before redistribution"


def validate_remoteclip_config() -> Path:
    """Require a real local RemoteCLIP checkpoint and fail loudly before any
    embedding/search process can silently fall back to generic OpenCLIP.
    """
    if not REMOTECLIP_CHECKPOINT.is_file():
        raise RuntimeError(
            "RemoteCLIP checkpoint not found. Stage the real local checkpoint at "
            f"{REMOTECLIP_CHECKPOINT} and set REMOTECLIP_CHECKPOINT_PATH if needed. "
            "The project intentionally does not fall back to OpenAI/OpenCLIP."
        )
    if REMOTECLIP_CHECKPOINT.suffix.lower() != ".pt":
        raise RuntimeError(
            "Unsupported RemoteCLIP checkpoint format. Expected an OpenCLIP "
            f"state-dict .pt file, received: {REMOTECLIP_CHECKPOINT}"
        )
    try:
        with REMOTECLIP_CHECKPOINT.open("rb") as checkpoint_file:
            checkpoint_file.read(1)
    except OSError as exc:
        raise RuntimeError(f"RemoteCLIP checkpoint is not readable: {REMOTECLIP_CHECKPOINT}") from exc
    return REMOTECLIP_CHECKPOINT

# ---- Change detection ----------------------------------------------------
# Fallback global threshold, used only until per-cluster calibration
# (Stage 12 / app/change/calibration.py) has run at least once.
DEFAULT_CHANGE_THRESHOLD = 0.22

# Quality gates -- a tile pair below these is suppressed regardless of
# embedding drift (Stage 13 false-alarm suppression).
MAX_CLOUD_FRACTION = 0.15
MIN_VALID_PIXEL_FRACTION = 0.80

# ---- Temporal signature / velocity -------------------------------------
VELOCITY_STABLE_THRESHOLD = 0.01
VELOCITY_ACCEL_SLOPE_THRESHOLD = 0.0015
VELOCITY_ACCEL_RATIO = 1.25

# Storyline candidate interpretation thresholds
STORYLINE_ONSET_THRESHOLD = 0.02
STORYLINE_ACTIVE_THRESHOLD = 0.05
STORYLINE_MAJOR_THRESHOLD = 0.09
STORYLINE_STABILIZING_THRESHOLD = 0.03

# ---- SAR fusion ---------------------------------------------------------
SAR_VV_WEIGHT = 0.45
SAR_VH_WEIGHT = 0.35
SAR_DIFF_WEIGHT = 0.20
SAR_VV_DELTA_SCALE = 3.5
SAR_VH_DELTA_SCALE = 3.5
SAR_DIFF_SCALE = 4.5
SAR_MIN_VALID_PIXELS = 0.50
SAR_MIN_CHANGE_SCORE = 0.18
SAR_ONLY_WEIGHT = 0.60
SAR_OPTICAL_MATCH_TOLERANCE_DAYS = 30
SAR_APPLY_SPECKLE_FILTER = False

# ---- Land-cover heuristic ----------------------------------------------
LANDCOVER_WATER_NDWI = 0.10
LANDCOVER_DENSE_VEG_NDVI = 0.55
LANDCOVER_SPARSE_VEG_NDVI = 0.28
