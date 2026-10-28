# SafePay AI project audit

Latest local re-verification: **42 backend tests and 12 frontend tests passed**, production build passed, and real browser prediction, validation, API-down and missing-model recovery paths were tested. A stale displayed assessment on form edits was fixed without redesigning the UI. See [LOCAL_VERIFICATION.md](LOCAL_VERIFICATION.md) for current commands/evidence; the initial implementation report below retains the earlier test counts as a historical record.

## Current implementation report — 2026-10-25

**This section supersedes the historical inspection below.** The user explicitly confirmed the application had never existed and authorized building SafePay AI from scratch. The former source-availability blocker has been resolved by creating the requested application. No previous UI, mock predictions or working model were replaced.

### Current architecture

React 19.1 / Vite 8.3.5 frontend with JavaScript, responsive navy/teal CSS, Lucide icons and lazy-loaded Recharts. Python 3.11.9 / FastAPI 0.162.0 / Starlette 1.10.0 / Uvicorn 0.54.0 / Pydantic 2.14.1 backend. scikit-learn 1.9.1 / Pandas 3.1.0 / NumPy 2.4.6 ML pipeline.

Eight validated signals pass through saved preprocessing and logistic regression. The model loads once at startup. Routes: `/health`, `/api/model`, `/api/predict`, `/api/predict/batch`, `/api/predict/csv`, generated `/docs`. History is the latest 200 assessment metadata records in React tab memory; no database/server persistence or accounts.

### Stage 1 — structure and dependencies

Files: backend package/app/ML directories, requirements files, frontend package/lockfile, HTML/Vite setup, `.gitignore`, environment examples. Created `.venv`, installed dependencies, checked Python/Node/npm, and inspected Git state. Initial sandbox network failures needed approved external execution. No credentials required. Detailed run commands are in README.md.

### Stage 2 — actual training and inference

Files: `backend/ml/train.py`, `backend/app/schema.py`, `backend/app/model.py`, `backend/app/main.py`, backend tests. Implemented strict ordered schema, seeded synthetic generator, stratified 60/20/20 splits, training-only transformations, class-weighted logistic regression, validation-only threshold selection, final test evaluation, trusted artifact loading and real single/batch inference. Prediction never trains or invents fallback scores.

Command: `python -m backend.ml.train`. Result: 16,000 synthetic records, real 5,025-byte artifact `synthetic-logreg-v1-1c00b747b8fb`; threshold 0.68; synthetic test precision 0.3632, recall 0.4667, F1 0.4085, ROC-AUC 0.7849, AP 0.4040; confusion matrix `[[2600,270],[176,154]]`. These are modest simulated-distribution results, not real-world validation.

No public dataset was downloaded/imported. Public ULB documentation was consulted, but the implemented fallback is explicitly synthetic; no claim is made that public data was technically impossible to obtain. Real-data use requires licensing, feature mapping and fresh evaluation.

### Stage 3 — performance

Files: model/API service, `backend/benchmark.py`, `frontend/src/api.js`, lazy chart component, PERFORMANCE.md. Implemented startup caching, vectorized batches, preprocessing/inference/pipeline logs, server timing headers, browser round-trip/overhead display and deferred charts.

Command: `python -m backend.benchmark --url http://127.0.0.1:8000`. Controlled local median comparisons: artifact reload 6.91 ms vs cached 4.61 ms; 100 individual calls 492.40 ms vs vectorized batch 5.36 ms. Warm preprocessing 4.28 ms dominates classifier arithmetic 0.253 ms. Local HTTP round trip median 7.83 ms, server processing 6.11 ms. JavaScript entry fell from 587.01 kB to 219.67 kB by deferring chart code. Scores match within 1e-12. See PERFORMANCE.md for conditions and percentiles. These are controlled alternatives, not historical application or cloud measurements.

### Stage 4 — UI and real API integration

Files: `frontend/src/App.jsx`, `main.jsx`, `styles.css`, `api.js`, `RiskDistribution.jsx`, frontend tests/setup, `examples/synthetic-transactions.csv`. Built responsive dashboard, eight-field form, actual results/timings/errors, CSV upload, session history search/filter/sort/pagination/details, actual metrics/confusion matrix, model/help/health sections, focus states and reduced-motion styles.

Live browser verification: default fictional form displayed 16.1%; changed fictional inputs produced a review alert; two-row CSV produced two results/one alert; history showed four session records; filters, risk sorting, details, analytics and charts worked. These observations are not hardcoded predictions. Desktop and 390×844 mobile layouts were inspected; mobile document width matched scroll width (375 CSS pixels excluding scrollbar), without horizontal page overflow. History intentionally clears on refresh. No fabricated real-world totals or multi-day trends exist.

### Stage 5 — security

Files: schema/model/API service, backend tests, environment examples, `frontend/vercel.json`, dependency manifests. Added strict finite/range/type checks, unknown-field rejection, 128 KiB streamed-body cap including chunked requests, 100-row cap, exact CSV headers, in-memory parsing, bounded per-process POST quota, explicit CORS, sanitized errors/logs, request IDs, error-path security headers, trusted-only model deserialization and frontend CSP/headers. Only a fixed synthetic CSV template is exported.

Initial frontend install reported four advisories; updated build/test tools resolved them. Initial Python audit reported 35 advisories across old pip/setuptools/Starlette; those were upgraded. Final `npm audit --json`: zero known vulnerabilities. Final `python -m pip_audit --format json --output reports/python-audit.json`: zero across 60 audited dependencies. `python -m pip check`: no broken requirements. This is not a security certification.

Not implemented: authentication/private-record authorization, centralized/trusted-proxy-aware rate limits, global inference concurrency caps, gateway upload deadlines, penetration testing, fairness/drift monitoring or compliance verification. Proxy clients may share a rate quota. No sensitive transaction data is stored.

### Stage 6 — tests, builds and deployment preparation

Files: backend/frontend tests, `pytest.ini`, `render.yaml`, `frontend/vercel.json`, requirements/manifests, README. Final `python -m pytest -q`: **42 passed**. Final `npm test`: **8 passed**. Final `npm run build`: successful, chart code split and original oversized-entry warning removed. `git diff --check` reported no whitespace errors but does not inspect newly untracked files. No lint/TypeScript command is configured.

Tests exercise real-pipeline consistency, batches, malformed/missing/extra/nonfinite fields, CSV/body/row limits, missing/corrupt/incompatible artifacts, one startup load, production CORS, rate limits, safe 500s, headers and concurrent inference. Frontend tests deliberately mock transport; separate real-browser checks verified localhost integration. The configured production bundle was also served with Vite preview and verified in the browser against the real local API; defaults again displayed 16.1%. This does not verify remote hosting. One nonfatal upstream Starlette TestClient warning recommends migrating from httpx to httpx2; current tests pass and the warning is not suppressed. Sandbox-isolated Python tests/socket access stalled or failed; approved external execution completed verification.

Render is configured to install dependencies, train offline during build and run Uvicorn on `$PORT`. Vercel is configured for the `frontend` root, Vite output and build-time API URL. **Neither cloud deployment is verified.** Remaining user actions: push a repository, connect hosting accounts, set actual domains/environment variables, deploy, then compare a fictional transaction using matching model versions. Exact steps and custom-domain CSP notes are in README.md. No credentials were requested or stored.

### Stage 7 — documentation and interviews

Files: README.md, INTERVIEW_PREPARATION.md, PERFORMANCE.md, this report and environment/CSV examples. Includes runnable setup, feature/API contract, Mermaid diagrams, dataset provenance/limitations, security scope, measured timings, deployment steps, 40 answered project-specific questions with follow-ups, truthful resume wording, a three-minute demo and troubleshooting. Personal contributions are not invented.

Local synthetic-data inference, UI integration, tests and build have been verified. Real-world detection quality and remote deployment remain unverified. Start servers with the README commands.

---

## Historical snapshot — before the user authorized implementation

The remaining text records the original empty-workspace inspection. Its missing-source inventory and blocker are historical and no longer describe the current workspace.

Audit date: 2026-10-25

## Stage 1: Repository inspection

The supplied workspace is `C:\Users\st854\OneDrive\Documents\ChatGPT\Fraud Transaction Detection`.

At inspection, this directory contained only `.git`. Git reports an unborn `master` branch, no commits, no other branches, and no configured remotes. There are no application files to audit or execute.

### Evidence

- `Get-ChildItem -Force`: only `.git` exists.
- `rg --files` excluding dependency and Git directories: no files found (exit 1).
- `git status --short`: no changes at initial inspection.
- `git log -5 --oneline`: current branch has no commits.
- `git branch -a`: no branches listed.
- `git ls-tree -r --name-only HEAD`: HEAD does not resolve.
- `git remote -v`: no remotes listed.
- Parent-directory inspection: no sibling project directories found.

### Architecture inventory

| Component | Observed status |
| --- | --- |
| Frontend and framework | Absent; cannot determine |
| Backend and API endpoints | Absent; cannot determine |
| Training and preprocessing code | Absent |
| Dataset and provenance | Absent |
| Saved model and feature schema | Absent |
| Database and migrations | Absent |
| Dependencies and runtime configuration | Absent |
| Tests and benchmarks | Absent |
| Render and Vercel configuration | Absent |

No transaction flow, model quality, latency, security controls, deployment status, or compatibility can be verified. No predictions or evaluation metrics have been generated. The absence of files here does not establish whether an application exists elsewhere.

## Prioritized implementation plan after source is available

1. Complete the architecture audit: inspect repository instructions, dependencies, frontend routes, API handlers, model artifacts, preprocessing, dataset provenance, storage, tests, and deployment configuration. Trace one transaction end to end and record defects by severity before editing application files.
2. Repair the actual prediction pipeline: validate the saved artifact and exact feature order, align preprocessing, implement consistent errors and response schemas, and verify real single and compatible batch inference.
3. Measure and optimize: benchmark representative inputs before changes, load the model at framework startup, vectorize batch inference, and measure preprocessing, inference, and request timing separately. Document local test conditions.
4. Improve the existing UI: retain useful design elements, implement accessible responsive dashboard sections, connect real API data, and clearly identify unavailable metrics or demo content.
5. Apply relevant security controls: strict schemas and upload limits, safe errors and logs, bounded requests, production CORS, environment configuration, minimum data retention, and safe exports. Choose persistence only if justified by the actual architecture.
6. Verify tests and deployment configuration: exercise input and CSV edge cases, missing-model failures, CORS, response contracts, frontend integration, production builds, and concurrency where practical. Configure Render and Vercel for the detected frameworks; separate local checks from account-dependent deployment verification.
7. Write documentation from verified implementation: README, environment examples, deployment and API instructions, and INTERVIEW_PREPARATION.md with architecture, limitations, measured results, at least 30 answered interview questions, truthful resume wording, and a demo script.

## Current blocker and required next step

Provide the existing project by placing its files in this workspace, giving the correct local project path, or providing its repository URL and intended branch. Source must include the model/training files where available; secrets and private financial data should not be supplied.

Stages 2–7 are pending source availability. A framework, model, dataset, database, or deployment has not been invented or substituted. No application test or production build can run without application files. No cloud credentials are required to resolve this initial source-location blocker.
