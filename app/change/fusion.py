"""Compatibility facade for modality fusion APIs."""
from .sar import SARObservation, fuse_modalities, sar_change_score, ingest_sar_manifest

__all__ = ["SARObservation", "fuse_modalities", "sar_change_score", "ingest_sar_manifest"]
