# SafePay general-purpose assistant (Groq)

The bottom-right assistant uses Groq through the FastAPI backend. Only the typed
question is sent to Groq; transaction records are never attached. Each question
is independent. The last ten exchanges live in browser memory until refresh.
Answers are plain text, not rendered HTML. The API does not log questions,
answers or credentials. Groq provider retention policies still apply.

## Configuration

Backend variables, documented with blank placeholders in root .env.example:

```text
GROQ_API_KEY=<your key>
GROQ_MODEL=openai/gpt-oss-20b
CHAT_DAILY_LIMIT=100
```

For local testing the user-authorized key is in Git-ignored root `.env`. Never
commit it or put it in a VITE_ variable. Replace the shared key after testing.
From the project root, stop any existing backend and run:

```powershell
& .\backend\start-local.ps1
```

The launcher loads only GROQ_API_KEY, GROQ_MODEL and CHAT_DAILY_LIMIT from `.env`.
Direct uvicorn commands do not load the file. In Render set these variables in
the backend service's Environment settings and restart/redeploy; the local key
is not uploaded. The frontend continues to use its existing VITE_API_BASE_URL.
No frontend secret, SDK or new dependency is required. OpenRouter is no longer
used by this integration; previous verification reports describe historical tests.

## Contract and limits

POST /api/chat accepts {"message":"Your question"} and returns {"answer":"..."}.
The server chooses the model, system instructions and generation settings.
Input is 1 to 1200 trimmed characters, with extra fields rejected. Groq uses
https://api.groq.com/openai/v1/chat/completions with JSON object mode, temperature
0.2, max_tokens 800 and low reasoning effort for GPT OSS models. Responses must
validate against the server's boolean/answer schema, finish normally, and contain
at most 4000 answer characters. Read limit is 64 KiB and request timeout 25 seconds.
No automatic retry, tool execution, browsing or fraud inference occurs in chat.

The existing payload limit, CORS allowlist and POST limiter remain. Additional
per-process chat limits are 10 calls/minute, 2 concurrent calls and 100 calls per
rolling 24 hours (configurable CHAT_DAILY_LIMIT). Failed attempts count. Limits
reset on restart and multiply across workers; they are not a durable spending
cap or authentication. Configure account-side spending limits in Groq as needed.

System instructions allow general questions and include verified SafePay facts.
Unsafe classifications become a fixed refusal. Prompt restrictions are not a
perfect security boundary and model answers may be inaccurate.

Errors: 422 invalid input; 429 local limit; 503 missing key, upstream rate limit,
authentication/permission or credit failure; 502 other provider or invalid-response
failure. Upstream rate-limit responses include Retry-After: 60 as retry guidance,
not a guarantee that quota resets in 60 seconds. Logs contain only provider HTTP
status or exception type, never response bodies or key values.

## Verification (2026-10-29)

- All 63 backend tests passed after migration, including Groq URL/model/payload,
  validation, sanitized failures, rate limits and malformed responses.
- Live local /api/chat returned HTTP 200 with an actual Groq explanation of
  precision in fraud detection. One observed round trip was 21.78 seconds; this
  is a single development-environment observation, not a performance guarantee.
- The originally attempted llama-3.1-8b-instant model returned model_not_found
  for this key. The verified default is openai/gpt-oss-20b instead.
- Frontend source is unchanged by migration; its tests/build were not rerun for
  this backend-only update (previous run: 19 tests and build passed).
- One existing Starlette/httpx test-client deprecation warning remains.
- No Git push or deployment was performed.

Official references: [Groq compatibility](https://console.groq.com/docs/openai),
[models](https://console.groq.com/docs/models),
[JSON object mode](https://console.groq.com/docs/structured-outputs).
