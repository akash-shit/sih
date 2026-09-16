"""Operational priority scoring; it reorders candidates but never confirms them."""
import json
import math
from app.config import PRIORITY_DISTANCE_DECAY_KM, PRIORITY_ZONE_DEFAULT_TIER


def _point(value) -> tuple[float, float] | None:
    if isinstance(value, dict):
        if "lat" in value and "lon" in value:
            return float(value["lat"]), float(value["lon"])
        if "latitude" in value and "longitude" in value:
            return float(value["latitude"]), float(value["longitude"])
    if isinstance(value, (tuple, list)) and len(value) >= 2:
        return float(value[0]), float(value[1])
    return None


def _center(row) -> tuple[float, float] | None:
    for value in (row, row.get("tile_center") if hasattr(row, "get") else None):
        point = _point(value)
        if point:
            return point
    if hasattr(row, "keys") and all(key in row.keys() for key in ("minlat", "maxlat", "minlon", "maxlon")):
        return ((float(row["minlat"]) + float(row["maxlat"])) / 2, (float(row["minlon"]) + float(row["maxlon"])) / 2)
    return None


def haversine_km(first: tuple[float, float], second: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*first, *second))
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(a))


def _inside(point: tuple[float, float], geojson: str | dict) -> bool:
    try:
        geometry = json.loads(geojson) if isinstance(geojson, str) else geojson
        geometry = geometry.get("geometry", geometry)
        if geometry.get("type") != "Polygon":
            return False
        x, y = point[1], point[0]
        polygon = geometry["coordinates"][0]
        inside = False
        for i, current in enumerate(polygon):
            previous = polygon[i - 1]
            if ((current[1] > y) != (previous[1] > y)) and x < (previous[0] - current[0]) * (y - current[1]) / (previous[1] - current[1]) + current[0]:
                inside = not inside
        return inside
    except (TypeError, ValueError, KeyError, IndexError, json.JSONDecodeError):
        return False


def compute_priority(candidate_row, aoi_row, confirmed_hotspots) -> float:
    score = 0.0
    reasons = []
    tier = (aoi_row.get("priority_tier") if hasattr(aoi_row, "get") else None) or PRIORITY_ZONE_DEFAULT_TIER
    score += {"high": 0.5, "medium": 0.3, "low": 0.1}.get(tier, 0.3)
    reasons.append("aoi_tier")
    center = _center(candidate_row)
    for hotspot in confirmed_hotspots or []:
        hotspot_point = _center(hotspot) or _point(hotspot)
        if center and hotspot_point:
            distance = haversine_km(center, hotspot_point)
            score += 0.4 * math.exp(-distance / PRIORITY_DISTANCE_DECAY_KM)
            candidate_id = hotspot.get("candidate_id", "") if hasattr(hotspot, "get") else ""
            reasons.append(f"near_confirmed_hotspot:{candidate_id}:{distance:.0f}km")
    polygon = aoi_row.get("priority_geojson") if hasattr(aoi_row, "get") else None
    if center and polygon and _inside(center, polygon):
        score += 0.3
        reasons.append("inside_priority_zone")
    value = max(0.0, min(1.0, score))
    if hasattr(candidate_row, "keys"):
        try:
            candidate_row["priority_score"] = value
            candidate_row["priority_reasons"] = json.dumps(reasons)
        except TypeError:
            pass
    return value


def strategic_priority(change_score: float, **kwargs):
    from .adaptive import strategic_priority as legacy
    return legacy(change_score, **kwargs)
