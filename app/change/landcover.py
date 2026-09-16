"""Heuristic land-cover context classification and adaptive optical weights."""
from app.config import LANDCOVER_DENSE_VEG_NDVI, LANDCOVER_SPARSE_VEG_NDVI, LANDCOVER_WATER_NDWI

LANDCOVER_WEIGHTS = {
    "dense_vegetation": (0.75, 0.25),
    "sparse_vegetation": (0.60, 0.40),
    "urban_bare": (0.45, 0.55),
    "water": (0.70, 0.30),
}
LAND_COVER_WEIGHTS = LANDCOVER_WEIGHTS


def classify_land_cover(ndvi_mean: float | None, ndwi_mean: float | None) -> str:
    if ndwi_mean is not None and ndwi_mean > LANDCOVER_WATER_NDWI:
        return "water"
    if ndvi_mean is not None and ndvi_mean > LANDCOVER_DENSE_VEG_NDVI:
        return "dense_vegetation"
    if ndvi_mean is not None and ndvi_mean > LANDCOVER_SPARSE_VEG_NDVI:
        return "sparse_vegetation"
    return "urban_bare"


def infer_land_cover(ndvi: float | None, ndwi: float | None) -> str:
    return classify_land_cover(ndvi, ndwi)


def optical_weights(land_cover: str | None) -> tuple[float, float]:
    return LANDCOVER_WEIGHTS.get(land_cover or "", (0.65, 0.35))


def adaptive_score(embedding_drift: float, spectral_delta: float, *, land_cover: str | None = None) -> float:
    embedding_weight, spectral_weight = optical_weights(land_cover)
    return max(0.0, min(1.0, embedding_weight * embedding_drift + spectral_weight * min(spectral_delta / 0.5, 1.0)))


__all__ = ["adaptive_score", "infer_land_cover", "classify_land_cover", "LAND_COVER_WEIGHTS", "LANDCOVER_WEIGHTS"]
