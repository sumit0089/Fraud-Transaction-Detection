# SafePay AI local re-verification

Verified on 2026-10-25 against the actual files in this workspace. No deployment was performed. This remains an educational synthetic-data application.

## Setup found and checked

- Backend: Python virtual environment `.venv`, pinned runtime/dev requirements, FastAPI app `backend.app.main:app`, trusted model at `backend/artifacts/model.joblib`.
- Frontend: React/Vite JavaScript, `frontend/package-lock.json`, npm scripts `dev`, `test`, `build`, `preview`. There is no configured lint or TypeScript command.
- Existing dependencies were complete: `python -m pip check` found no conflicts; `npm ls --depth=0` matched the package manifest. Reinstallation was unnecessary.
- Vite development defaults to `http://127.0.0.1:8000` as its API URL. Production requires `VITE_API_BASE_URL`; the test covering missing production configuration passed. Vite reads `frontend/.env.local`; FastAPI reads process environment rather than implicitly loading `.env`.

## Fresh checks actually executed

| Command | Result |
| --- | --- |
| `.\.venv\Scripts\python.exe -m pip check` | No broken requirements |
| `npm ls --depth=0` in `frontend` | Installed direct dependencies match |
| `.\.venv\Scripts\python.exe -m pytest -q` | 42 passed, 1 upstream deprecation warning, 7.16 seconds |
| Initial `npm test` | 8 passed |
| Final `npm test`, after regression additions/fix | 12 passed, 4.77 seconds |
| Final `npm run build` | Passed, 1.26 seconds; entry 219.71 kB / 69.77 kB gzip; chart deferred |
| Lint/type check | Not configured; not claimed as run |

New regression tests initially exposed the retained-score issue while test selectors were being refined. The final run has **zero failing tests**. The existing backend fault-injection test verified a sanitized HTTP 500 without leaking internal error text.

One remaining nonfatal warning comes from Starlette TestClient: use of httpx is deprecated in favor of httpx2. The current pinned stack's tests pass; no warning was hidden or treated as a passed functional check.

## Live HTTP and browser verification

Both services were started on localhost outside the tool's restricted socket sandbox. The browser used `http://127.0.0.1:5173/`, not a `file://` URL.

| Scenario | Observed result |
| --- | --- |
| Health with normal artifact | HTTP 200, `status=ready`, `model_ready=true` |
| Model endpoint | HTTP 200; ordered eight-feature contract and actual artifact version |
| Actual form submission | Browser submitted fictional values; score 0.1614408350121734 returned by API, displayed as 16.1%, classification below review threshold |
| Saved pipeline comparison | Live API result exactly matched `ModelService` using the saved artifact for the same input |
| Negative amount | Browser range validation blocked submission; direct API returned 422 with `body.amount` |
| Blank/missing values | Browser required validation blocked submission; direct empty JSON returned 422 listing all eight missing fields |
| Allowed origin | Preflight from `http://127.0.0.1:5173`: 200 and matching allow-origin |
| Untrusted origin | Preflight from `https://untrusted.example`: 400, no allow-origin |
| API deliberately stopped | Form displayed a connection error, no invented prediction, submit became usable again |
| Model deliberately unavailable | API started with a nonexistent `MODEL_DIR`; health returned 503/degraded and form displayed the actual model-unavailable 503 message |
| Recovery | Temporary degraded API stopped; normal API restarted with existing artifact; form again displayed the genuine 16.1% score |

Raw initial HTTP evidence is saved locally in `reports/local-verification.json` (generated output, ignored by Git). Browser checks use real requests; frontend unit tests deliberately mock transport.

## Genuine issue fixed

`frontend/src/App.jsx` retained the previous assessment when a user edited an input. An invalid new amount could therefore appear beside an old score even though native validation blocked a new request.

Added `updateForm` to clear the displayed assessment and previous error on edits. Inputs are disabled during an active analysis so edited values cannot be mistaken for the transaction being processed. The layout, model behavior, backend and saved artifact are unchanged. Four regression cases in `frontend/src/App.test.jsx` cover numeric/category/flag edits and in-flight input locking.

## Startup loading / no request-time training

Source inspection confirms model construction is in the FastAPI lifespan, and no `train`/`fit` call exists in the prediction handlers. The existing `test_model_loaded_once` passed: three requests caused one service initialization within one lifespan. API requests never fall back to training when a model is absent; the deliberate missing-model run returned 503.

The artifact SHA-256 before requests was `0fefd0610e5857f52ce39f2b1e9e519d041f36295c94130f14a4f235c4017efb`; verification checks compare it again after requests/failure recovery. A test fixture trains a separate temporary model for backend tests; that is not API request-time training.

## Exact Windows PowerShell commands

For this workspace, dependencies and the trained artifact already exist. Start each service in its own terminal.

**Terminal 1 — backend:**

```powershell
Set-Location 'C:\Users\st854\OneDrive\Documents\ChatGPT\Fraud Transaction Detection'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

**Terminal 2 — frontend:**

```powershell
Set-Location 'C:\Users\st854\OneDrive\Documents\ChatGPT\Fraud Transaction Detection\frontend'
npm run dev -- --port 5173 --strictPort
```

Open http://127.0.0.1:5173/ . Health: http://127.0.0.1:8000/health . Stop either terminal's process with Ctrl+C. Do not start duplicate servers while these ports are already in use.

For a **fresh checkout only**, before starting the backend:

```powershell
Set-Location 'C:\Users\st854\OneDrive\Documents\ChatGPT\Fraud Transaction Detection'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m backend.ml.train
Set-Location frontend
npm ci
```

If an explicitly configured API origin is desired in the frontend, set `$env:VITE_API_BASE_URL='http://127.0.0.1:8000'` in its terminal before starting Vite. Set `CORS_ORIGINS` in the backend terminal before starting Uvicorn if using other origins. Existing examples contain no secrets.

## Remaining boundaries

No failing functional tests remain. No lint command is configured, and the upstream TestClient warning remains. Synthetic model quality does not establish real financial fraud detection. Hosting, real-data validity and production security are unverified. No cloud resources were deployed.
