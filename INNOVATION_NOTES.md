# Innovation Notes

This repository was extended only through the Phase 1 temporal-signature foundation, which remains additive and backward compatible with the original optical-only detector.

## Implemented in this pass

- Added a pure effective-score selector and velocity computation in [app/change/temporal_signature.py](app/change/temporal_signature.py).
- Added classified storyline stage logic in [app/change/storyline.py](app/change/storyline.py).
- Added named temporal-signature config constants in [app/config.py](app/config.py).
- Added additive DB columns for velocity and land-cover metadata via the existing migration helper in [app/geospatial/catalog_db.py](app/geospatial/catalog_db.py).
- Added a focused regression test in [tests/test_velocity.py](tests/test_velocity.py).

## Not implemented in this pass

The remaining innovation phases in the master prompt (SAR fusion, land-cover adaptive scoring, strategic priority scoring, active-learning reranking, heatmaps, self-calibration, optional LLM brief, and the broader frontend/backend API surface) are intentionally not forced into the existing codebase in a way that would break optical-only scoring or existing API compatibility. The repository’s current optical detector and SQLite schema remain the ground truth.

This record exists to document that the full multi-phase upgrade is a larger project and should be implemented in smaller additive layers, with each phase validated against the existing test suite before the next is introduced.
