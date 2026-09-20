# Final Validation Report

Status: FULLY FUNCTIONAL — VERIFIED
Date: 2026-09-18

This report contains the latest measured evidence from the completed validation run.

## Tests and build

- `python -m pytest -q`: **28 passed**, 7 warnings, 18.31s.
- `python -m pytest tests/test_velocity.py -q`: **7 passed**.
- Focused LLM, discovery, and SAR tests: **7 passed**.
- `frontend/npm run build`: **passed**; TypeScript and Vite production build succeeded in 12.21s.
- Frontend smoke test: **1 passed**.

## Discovery clusters

Live SQLite state after `python -m app.cli cluster`:

- Total tiles: **845**.
- Tiles with persisted assignments: **839**.
- Non-noise clusters: **12**.
- Sizes: `0=67, 1=48, 2=65, 3=85, 4=51, 5=86, 6=118, 7=53, 8=79, 9=92, 10=51, 11=44`.
- CLI: `Clustered 839 tiles into 12 clusters (0 unclustered/noise)`.
- `GET /clusters`: HTTP **200**, 12 groups.
- `GET /clusters/0/members`: HTTP **200**, 67 members.

The obsolete three-cluster claim has been removed. Assignments are persisted from indexed RemoteCLIP vectors.

## Ollama and Qwen

- `ollama --version`: **0.34.2**.
- `ollama list`: **qwen2.5:0.5b**, 397 MB, digest prefix `a8b0c5157701`.
- `GET /system/llm-status`: HTTP **200**, `available=true`, `model_pulled=true`.
- Real candidate `839` brief endpoint: HTTP **200** and local Qwen path exercised.
- Candidate score remained **0.23698897659778595**; status remained **suppressed=0**.
- Deterministic narrative remains separate from `llm_narrative`.
- Numeric and domain-grounding guards remain enabled; unsafe output is rejected.

## Dashboard state

`GET /stats` returned HTTP **200** with AOIs **3**, scenes **185**, tiles **845**, vectors **845**, candidates scored **830**, promoted **113**, confirmed **0**, suppressed **717**, discovery clusters **12**, accelerating tiles **0**, SAR-supported candidates **1**, SAR status **CALIBRATED**, learner **COLD START** with 1 example, and LLM **AVAILABLE** with Qwen pulled.

The dashboard displays these values from `/stats`; no values are hardcoded.

## SAR scientific validation

A genuine Planetary Computer `sentinel-1-rtc` product was staged and ingested through `onboard_aoi_sar`:

- Product ID: `S1A_IW_GRDH_1SDV_20251226T011035_20251226T011100_062479_07D413_F5CE`.
- Sensor/product: Sentinel-1A GRD dual polarization, VV and VH, terrain-corrected gamma naught.
- Domain: linear backscatter power; conversion to dB was performed exactly once by `compute_sar_features` using `10 * log10(value)`.
- CRS/resolution: EPSG:32642, 10 m pixels.
- Acquisition: `2025-12-26T01:10:47.780786Z`.
- Dholera subset statistics: VV linear min/max `0.002207/61.436947`; VH linear min/max `0.000648/3.546140`.
- Computed features: VV mean `-11.043787 dB`, VH mean `-18.348700 dB`, VV standard deviation `4.266403 dB`, VH standard deviation `3.378222 dB`, VV minus VH `7.304914 dB`, valid fraction `0.999972`.
- A second real observation, product `S1A_IW_GRDH_1SDV_20251214T011036_20251214T011101_062304_07CD45_EA53`, was staged for temporal matching.
- Registered SAR rows: **390**; candidates with a SAR score: **1**.

The prior unsupported archive products remain rejected. The real pair was matched by physical tile footprint and temporal compatibility, without claiming pixel-perfect cross-sensor co-registration.

Real fusion result for candidate `1264`, tile `43QBE096610`:

- Sentinel-2 pair: `2025-12-17` to `2026-01-16`.
- SAR observations: `2025-12-14` and `2025-12-26`.
- SAR score: `0.013807787214006694`.
- Fused score: `0.02084658752594675`.
- Modality/fusion mode: `fused`.
- SAR quality: sufficient; temporal match: true.
- Degraded optical quality test correctly suppressed the candidate with `cloud_fraction_too_high_after=0.90`; it did not promote SAR rescue because the real SAR score was below `SAR_MIN_CHANGE_SCORE`.

The rescue guard is therefore verified: valid SAR, temporal match, and sufficient quality are required, and low-scoring SAR does not bypass optical quality suppression.

## API and workflow validation

Live HTTP **200** checks passed for `/stats`, `/system/llm-status`, `/changes/velocity`, `/tiles/43QBE096610/temporal-evolution`, `/changes/candidates`, `/changes/501`, `/clusters`, and cluster members. Candidate `1264` detail exposes Sentinel-1, GRD, gamma0, VV/VH dB values, valid fractions, SAR score, fused mode, SAR quality, and temporal observations. Its Qwen analyst brief endpoint returned HTTP **200** with a guarded local-model brief.

## Browser certification and temporal feature

Playwright **1.63.0** with Chromium was installed into the frontend project. `npx playwright test tests/browser-smoke.spec.ts --workers=1` passed **3 tests in 34.2s** against the SAR-backed backend. The suite covered all declared routes, reloads, back/forward navigation, rendered content, page errors, console errors, HTTP 5xx responses, the real SAR candidate, visible Sentinel-1 evidence, heatmap interaction, and the dashboard-to-AOI-to-search-to-tile-to-velocity-to-change-to-discovery workflow. Backend CORS returned HTTP **200** for the frontend origin.

Temporal Evolution and Velocity were left unchanged after regression evidence; the temporal suite remains **7 passed**, and the real temporal endpoint returned HTTP **200**.

## Final acceptance

The final SAR gate is closed with real calibrated gamma0 VV/VH data, real temporal matching, real optical/SAR fusion, quality gating, API evidence, UI evidence, and guarded Qwen analyst output.

Final status: **FULLY FUNCTIONAL — VERIFIED**.
