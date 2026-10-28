# SafePay AI performance verification

Measured locally on 2026-10-25, Windows build 26300, Python 3.11.9, scikit-learn 1.9.1, Pandas 3.1.0, NumPy 2.4.6. Artifact `synthetic-logreg-v1-1c00b747b8fb`, 5,025 bytes. One local Uvicorn process. No cloud/WAN/platform cold start was measured.

## Controlled comparisons

There was no earlier application. Baselines below are deliberately measured alternatives, not historical production behavior. Each pair uses the same generated inputs/artifact and checks score equality within absolute tolerance 1e-12. OS filesystem caches are warm; other local work affects timings.

```powershell
.\.venv\Scripts\python.exe -m backend.benchmark --url http://127.0.0.1:8000
```

Run from the repository root with the API running. Raw output: `reports/benchmark.json` (generated/ignored by Git). Inputs: 100 fictional records, seed 77; one batch warm-up before timed comparisons.

| Operation | Baseline median / p95 | Implemented median / p95 | Samples |
| --- | --- | --- | --- |
| Single call: reload artifact vs startup-cached model | 6.91 / 9.47 ms | 4.61 / 6.50 ms | 150 paired calls |
| 100 records: individual calls vs vectorized batch | 492.40 / 574.85 ms | 5.36 / 8.65 ms | 15 paired batches |

Under these conditions caching reduced median single-call time by about 33%; batching reduced median 100-record time by about 99% (roughly 92×). These comparisons exclude HTTP and schema parsing. They do not mean internet requests become 92× faster.

## Component measurements

| Component | Median | p95 | Samples |
| --- | --- | --- | --- |
| DataFrame + fitted preprocessing | 4.28 ms | 6.07 ms | 150 single calls |
| Classifier `predict_proba` | 0.253 ms | 0.433 ms | 150 single calls |
| Local HTTP client round trip | 7.83 ms | 10.47 ms | 50 requests |
| Server processing header | 6.11 ms | 8.06 ms | Same 50 |
| Transport/client overhead estimate | 1.73 ms | 2.48 ms | Same 50 |
| HTTP round trip, 4 client threads | 28.08 ms | 37.32 ms | 16 requests |

Repeated Pandas/transformer setup dominates classifier arithmetic in the warm model path. Vectorized inference transforms a batch once; fitted transformations and classifier behavior are unchanged. Startup caching avoids repeat deserialization. Concurrency measurements verify modest successful load, not production capacity. Synchronous ML runs in a threadpool; global inference concurrency/gateway limits remain future work.

## Browser observations and timing interpretation

Actual browser submissions against localhost produced these observations:

| Example | Preprocessing | Inference | Server | Browser round trip | Approximate overhead |
| --- | --- | --- | --- | --- | --- |
| Fictional default form | 10.79 ms | 0.53 ms | 13.70 ms | 38.20 ms | 24.50 ms |
| Second fictional input | 5.90 ms | 0.44 ms | 8.52 ms | 18.10 ms | 9.58 ms |

These two observations are not percentile estimates or before/after optimization evidence. They preceded the final middleware-order change extending header timing to bounded body reception. The final HTTP table above uses the final middleware. A two-row CSV upload also succeeded, with an observed round trip of 178.20 ms during other local work. Isolated observations are not latency guarantees.

Frontend `performance.now()` measures fetch through JSON parsing. Backend `perf_counter()` separately measures preprocessing, inference and pipeline work. Final middleware timing includes bounded body reception, validation, scheduling, handler work and response preparation, ending before final transmission. Browser/client minus server includes transport, client/browser work and excluded delivery; it is not pure network time. Negative residuals from precision are clamped to zero; no clock synchronization is assumed.

Python imports, model initialization and host wake-up happen before readiness. Warm measurements do not describe deployed cold starts. Remote latency requires actual Render/Vercel deployment and measurements.

## Frontend bundle

Initial production entry: 587.01 kB JavaScript (167.44 kB gzip). Lazy Recharts loading: 219.67 kB entry (69.74 kB gzip), plus a deferred 368.68 kB chart chunk (98.40 kB gzip). Charts load only when session data exists and a distribution is displayed. This is a measured bundle-size change, not a measured page-load-time improvement; the UI is preserved.

## Regression coverage

Scores are compared with the saved full pipeline, individual/batch scores within 1e-12, and CSV results with JSON results. Startup load count, invalid inputs, model failures, body/CSV limits, CORS, safe errors, rate limits and concurrency are tested. Frontend tests verify typed payloads, actual returned scores, timing headers, CSV transport, errors/timeouts and missing production API configuration.

Initial implementation checks: 42 backend tests, 8 frontend tests, successful production build and dependency compatibility check. Subsequent local re-verification passed 42 backend and 12 frontend tests after a UI stale-result fix; see LOCAL_VERIFICATION.md. No lint or TypeScript command is configured.

Production smoke test: rebuilt with VITE_API_BASE_URL=http://127.0.0.1:8000, served compiled dist with Vite preview on the allowed 5173 origin, and submitted the real form in the browser. It returned the same 16.1% displayed default score. Observed timings: preprocessing 13.29 ms, inference 0.59 ms, server 15.90 ms, browser round trip 27.30 ms, overhead 11.40 ms. This verifies a configured production bundle locally, not hosted deployment.
