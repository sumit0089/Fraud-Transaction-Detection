import csv
import io
import logging
import os
import time
import uuid
from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from backend.app.model import ModelService
from backend.app.chat import ChatInput, ChatService
from backend.app.schema import Batch, BatchResponse, FEATURES, PredictionResponse, Transaction

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("safepay")
MAX_BODY = 128 * 1024
DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[1] / "artifacts"


class RequestLimits:
    """Bound streamed bodies before parsing; bounded per-process demo rate limiter."""
    def __init__(self, app, limit):
        self.app, self.limit = app, limit
        self.clients = OrderedDict()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if scope["method"] == "POST":
            now = time.monotonic()
            client = (scope.get("client") or ("unknown",))[0]
            queue = self.clients.setdefault(client, deque())
            self.clients.move_to_end(client)
            while queue and queue[0] < now - 60:
                queue.popleft()
            if len(self.clients) > 4096:
                self.clients.popitem(last=False)
            if len(queue) >= self.limit:
                return await JSONResponse({"error": {"code": "rate_limited", "message": "Too many requests. Try again in one minute."}}, status_code=429, headers={"Retry-After": "60"})(scope, receive, send)
            queue.append(now)
        # Buffer at most MAX_BODY, including requests without Content-Length.
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > MAX_BODY:
                return await JSONResponse({"error": {"code": "payload_too_large", "message": "Request exceeds 128 KiB."}}, status_code=413)(scope, receive, send)
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()
        await self.app(scope, replay, send)


def create_app(model_dir=None, rate_limit=None):
    directory = model_dir or os.getenv("MODEL_DIR", str(DEFAULT_MODEL_DIR))

    @asynccontextmanager
    async def lifespan(app):
        app.state.model = None
        try:
            app.state.model = ModelService(directory)
            logger.info("model_ready version=%s", app.state.model.metadata["model_version"])
        except Exception as exc:
            # Do not leak artifact paths, contents, or exception details to clients.
            logger.error("model_unavailable type=%s", type(exc).__name__)
        yield
        app.state.model = None

    app = FastAPI(title="SafePay AI", version="1.0.0", lifespan=lifespan)
    chat_service = ChatService()

    @app.post("/api/chat")
    async def chat(payload: ChatInput):
        return await chat_service.answer(payload.message)
    app.add_middleware(RequestLimits, limit=rate_limit if rate_limit is not None else int(os.getenv("RATE_LIMIT_PER_MINUTE", "120")))

    @app.middleware("http")
    async def timing(request, call_next):
        start = time.perf_counter()
        request_id = uuid.uuid4().hex
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error("request_failed id=%s type=%s", request_id, type(exc).__name__)
            response = JSONResponse({"error": {"code": "internal_error", "message": "Request could not be processed."}}, status_code=500)
        duration = (time.perf_counter() - start) * 1000
        response.headers.update({"X-Request-ID": request_id, "X-Request-Time-Ms": f"{duration:.3f}",
            "Server-Timing": f"app;dur={duration:.3f}", "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer", "Cache-Control": "no-store"})
        logger.info("request id=%s method=%s status=%s total_ms=%.3f", request_id, request.method, response.status_code, duration)
        return response

    origins = [s.strip() for s in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if s.strip()]
    if "*" in origins:
        raise ValueError("CORS_ORIGINS must list explicit origins")
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
                       expose_headers=["X-Request-Time-Ms", "X-Request-ID", "Server-Timing"])

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request, exc):
        # Pydantic errors can contain the submitted input; omit it.
        fields = [".".join(map(str, e["loc"])) for e in exc.errors()]
        message = "Invalid chat message (1 to 1200 characters required)." if request.url.path == "/api/chat" else "Invalid or missing transaction fields."
        return JSONResponse({"error": {"code": "invalid_input", "message": message, "fields": fields}}, status_code=422)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse({"error": {"code": f"http_{exc.status_code}", "message": str(exc.detail)}}, status_code=exc.status_code, headers=exc.headers)

    def model():
        service = getattr(app.state, "model", None)
        if service is None:
            raise HTTPException(503, "Model unavailable. Run offline training and restart the API.")
        return service

    async def infer(transactions):
        output = await run_in_threadpool(model().predict, transactions)
        logger.info("prediction count=%d preprocessing_ms=%.3f inference_ms=%.3f pipeline_ms=%.3f", len(transactions), *output["timings"].values())
        return output

    @app.get("/health")
    def health():
        ready = getattr(app.state, "model", None) is not None
        return JSONResponse({"status": "ready" if ready else "degraded", "model_ready": ready}, status_code=200 if ready else 503)

    @app.get("/api/model")
    def metadata():
        return {**model().metadata, "input_schema": Transaction.model_json_schema()}

    @app.post("/api/predict", response_model=PredictionResponse)
    async def predict(transaction: Transaction):
        output = await infer([transaction])
        return {"result": output["results"][0], "timings": output["timings"]}

    @app.post("/api/predict/batch", response_model=BatchResponse)
    async def batch(payload: Batch):
        return await infer(payload.transactions)

    @app.post("/api/predict/csv", response_model=BatchResponse)
    async def csv_predict(request: Request):
        if request.headers.get("content-type", "").split(";")[0] != "text/csv":
            raise HTTPException(415, "Send CSV with Content-Type: text/csv.")
        try:
            text = (await request.body()).decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text), strict=True)
            if reader.fieldnames != FEATURES:
                raise HTTPException(422, "CSV columns must match the documented feature order exactly.")
            rows = []
            for row in reader:
                if len(rows) >= 100:
                    raise HTTPException(422, "CSV must contain 1 to 100 rows.")
                if None in row or any(v is None for v in row.values()):
                    raise ValueError("Invalid column count")
                for name in ["amount", "distance_km"]:
                    row[name] = float(row[name])
                for name in ["hour", "transactions_24h", "account_age_days"]:
                    row[name] = int(row[name])
                for name in ["international", "new_device"]:
                    if row[name].lower() not in ("true", "false"):
                        raise ValueError("Boolean must be true or false")
                    row[name] = row[name].lower() == "true"
                rows.append(Transaction.model_validate(row))
            if not rows:
                raise ValueError("Empty CSV")
        except (UnicodeError, ValueError, csv.Error, ValidationError):
            raise HTTPException(422, "Malformed CSV or invalid transaction values; use the provided template.") from None
        return await infer(rows)

    return app


app = create_app()
