# Performance report

## Scope

This optimization pass focused on the hot paths for the velocity list, review queue, and learner model loading while preserving existing semantics and scores.

## Optimizations implemented

- Velocity list endpoint now paginates with `limit` / `offset` and returns a compact default payload.
- Review queue endpoint now accepts `limit` / `offset` and keeps sorting server-side.
- Active learner cache avoids repeated pickle deserialization on each request.
- Database indexes were added in the migration phase for the heavy filters and sort keys.
- The frontend velocity page requests only the first page and adds a lightweight "Load more" pattern.

## Cache strategy

- Active learner model: in-memory cached singleton keyed by model path.
- Quality summary: already cached with TTL in the request layer.
- Velocity page: page-level request throttling via query key and lazy page expansion.

## Pagination strategy

- Velocity: default `limit=8`, optional `offset`.
- Review queue: default `limit=24`, optional `offset`.
- Frontend: renders only the first page and loads more as the user asks.

## Lazy loading strategy

- Temporal evolution remains a demand-driven endpoint.
- Velocity cards use compact series data only, instead of forcing full heavy temporal payloads on the first render.
- Full temporal evolution and detailed frames stay behind the tile-level expansion path.

## Database indexes added

- `idx_tiles_aoi_date` on `tiles(aoi_id, acquisition_date)`
- `idx_tiles_cluster` on `tiles(cluster_id)`
- `idx_candidates_score` on `change_candidates(combined_score DESC, candidate_id DESC)`
- `idx_candidates_priority` on `change_candidates(priority_score DESC, candidate_id DESC)`
- `idx_candidates_predicted` on `change_candidates(predicted_confirm_prob DESC, candidate_id DESC)`

## Actual measured timings

The timings below were measured with the current optimized code after the fix work:

| Endpoint | Status | Time (ms) |
| --- | --- | ---: |
| /stats | 200 | 2137.8 |
| /changes/velocity | 200 | 30722.1 |
| /changes/candidates | 200 | 970.2 |
| /changes/candidates/data-quality | 200 | 8789.6 |
| /clusters | 200 | 103.5 |

## Verification evidence

- Python regression suite: `python -m pytest -q` -> 30 passed in 33.33s
- Frontend build: `cd frontend && npm run build` -> successful Vite production build

## Important note about “before” measurements

A valid pre-optimization baseline was not captured in this session because the initial profiling command failed before output was produced. This report intentionally records only factual numbers that were measured in this environment and does not invent a before/after improvement percentage.
