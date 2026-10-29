# Local functional verification, 2026-10-29

Targets: Vite at http://127.0.0.1:5173 and FastAPI at http://127.0.0.1:8000.
This checks a local educational application, not real financial data or deployed
Render/Vercel behavior. Existing UI and prediction model were preserved.

## Automated checks actually executed

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm test
npm run build
```

- Backend initially 58 passed; after adding five provider HTTP-error regressions,
  **63 passed**, 0 failed, in 11.20 seconds. One Starlette/httpx TestClient
  deprecation warning remains. No runtime dependency migration was attempted.
- Frontend **19 passed**, 0 failed, in 6.86 seconds.
- Vite production build passed in 1.45 seconds. There is no configured standalone
  lint or TypeScript check in package.json; neither is reported as passed.
- Backend tests cover saved-pipeline consistency, model loading once, missing or
  corrupt artifacts, invalid/nonfinite/missing fields, batch bounds, CSV schema,
  body limits, concurrency, rate limits, sanitized inference errors and CORS.
- Frontend tests cover prediction integration, API failure/timeout handling,
  production URL configuration, input locking, stale-result clearing, themes,
  animated navigation state, clear-history confirmation, and chat success/errors.
  Provider responses in automated tests are mocked.

## Running API checks

| Check | Observed result |
| --- | --- |
| GET /health | 200, model_ready true |
| Low synthetic input | 200, legitimate, score 0.07168888615781344 |
| High synthetic input | 200, fraud alert, score 0.9999999991083104 |
| Missing prediction fields | 422 |
| Negative amount | 422 |
| Two-input JSON batch | 200, two actual assessments |
| Wrong CSV columns | 422 with schema message |
| 131073-byte body | 413 |
| Origin http://127.0.0.1:5173 | Correct Access-Control-Allow-Origin |
| Origin https://untrusted.example | No Access-Control-Allow-Origin |

A disallowed-origin GET may return 200: CORS withholds browser access; it is not
authentication. These are individual local checks, not a latency benchmark.

## Real browser checks

- Empty amount: native required-field error; negative amount: range error.
- Reset and submit default fictional transaction: actual model result displayed
  16.1%, model version and preprocessing/inference/server/browser timings.
- Upload examples/synthetic-transactions.csv: two results, one review alert.
- Upload reports/qa-malformed.csv: server schema error displayed. A subsequent
  valid upload succeeded, demonstrating error recovery.
- Upload reports/qa-pagination.csv (eight fictional rows): eight assessments,
  four alerts, bringing browser session totals to 11 results and five alerts.
- Search by transaction-ID prefix, fraud-only filter, highest-risk sorting and
  transaction details worked. Pagination showed eight rows then three rows,
  and returned to page one correctly.
- Clear-history dialog focused Keep history; cancelling preserved all 11 records.
  Confirmed deletion is covered by automated tests; browser records were retained.
- Analytics showed the live 11-result distribution and actual saved evaluation
  metrics. About the model and Help center rendered successfully.
- System health displayed model readiness. The local backend was stopped for a
  controlled offline test: Refresh displayed the connection failure. Restarting
  with backend/start-local.ps1 and clicking Retry restored Model ready.
- Phone viewport 375x812: document/client width both 360px excluding scrollbar;
  no horizontal page overflow. Mobile menu navigation worked. Light theme was
  inspected and original dark theme/default viewport restored.

## Chat failure found and addressed

The question "What is precision in fraud detection? Answer in one sentence."
reproduced the generic 502 after approximately 22 seconds. A separate direct
provider diagnostic then returned HTTP 429. This confirms upstream rate limiting
during testing; it does not prove the cause of every earlier generic failure.

backend/app/chat.py now maps upstream 429 to a clear provider-rate-limit message
(503 with Retry-After: 60); authentication/permission and credit failures also
have distinct sanitized messages. Other provider errors remain sanitized. Logs
include only HTTP status or exception type, never keys, prompts or response bodies.
Five new tests verify these mappings and secrecy. No automatic paid retry or
model switch was added. Provider reliability cannot be guaranteed locally.
After restarting, the same browser question displayed the new explicit provider
rate-limit message, retained the question and re-enabled Send. Screenshot:
`reports/safepay-functional-verification.png`. The API and frontend remain running.

## Limits and remaining checks

- No deployment or Git push was performed. Deployed URLs, production environment
  variables, hosted cold starts, and production CSP behavior were not retested.
- An OpenRouter key remains only in ignored root .env for authorized local testing;
  git check-ignore confirmed exclusion. Rotate the exposed testing key afterwards.
- This is not a full security audit, load test or accessibility certification.
- Reduced-motion handling was checked in source; OS reduced-motion preference
  was not changed during this run.
- Historical live chat replies have succeeded, but the reproduced rate limiting
  means chat must not be described as consistently working.
