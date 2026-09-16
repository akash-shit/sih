# Innovation Notes

This repository was extended only through the Phase 1 temporal-signature foundation, which remains additive and backward compatible with the original optical-only detector.

## Implemented in this pass

- Added a pure effective-score selector and velocity computation in [app/change/temporal_signature.py](app/change/temporal_signature.py).
- Added classified storyline stage logic in [app/change/storyline.py](app/change/storyline.py).
- Added named temporal-signature config constants in [app/config.py](app/config.py).
- Added additive DB columns for velocity and land-cover metadata via the existing migration helper in [app/geospatial/catalog_db.py](app/geospatial/catalog_db.py).
- Added a focused regression test in [tests/test_velocity.py](tests/test_velocity.py).

## Not implemented in this pass

The v0.2 innovation layer is implemented additively. SAR is limited to
backscatter-delta change detection on Sentinel-1 GRD/monthly mosaic VV/VH
data; it is not interferometric coherence. Land-cover labels are heuristic,
priority and active learning are analyst-facing ranking signals, and heatmaps
are explanatory rather than ground-truth evidence. Scientific metrics and
real-data SAR sanity checks remain pending until representative products are
available.

This record exists to document that the full multi-phase upgrade is a larger project and should be implemented in smaller additive layers, with each phase validated against the existing test suite before the next is introduced.
