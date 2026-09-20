# Performance baseline

This session did not capture a valid pre-optimization baseline due a shell redirection issue during the initial profiling command in PowerShell. The command failed before the timing output could be collected, so no dependable baseline numbers are available to report without inventing values.

## What was actually measured

The following timings were captured after the performance fix work and are therefore the current measured performance state, not a before/after delta:

| Endpoint | Status | Time (ms) |
| --- | --- | ---: |
| /stats | 200 | 2137.8 |
| /changes/velocity | 200 | 30722.1 |
| /changes/candidates | 200 | 970.2 |
| /changes/candidates/data-quality | 200 | 8789.6 |
| /clusters | 200 | 103.5 |

## Notes

- The velocity endpoint now uses server-side pagination with a default limit of 8 and optional offset.
- The candidate queue now supports `limit` and `offset` and returns only the first page by default.
- The learner model is cached in memory to avoid reloading the active model on every request.
- The report still reflects that a true before/after benchmark requires a clean pre-change capture in a separate run.
