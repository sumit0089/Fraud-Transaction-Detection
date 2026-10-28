"""The shared, ordered contract used for training, inference, and UI fields."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field

FEATURES = ["amount", "hour", "transactions_24h", "distance_km", "account_age_days", "international", "new_device", "merchant_category"]
NUMERIC = FEATURES[:5]
CATEGORIES = ["retail", "grocery", "travel", "entertainment", "transfer"]


class Transaction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    amount: Annotated[float, Field(ge=0.01, le=1_000_000, description="Synthetic currency units")]
    hour: Annotated[int, Field(ge=0, le=23)]
    transactions_24h: Annotated[int, Field(ge=1, le=100)]
    distance_km: Annotated[float, Field(ge=0, le=20_000)]
    account_age_days: Annotated[int, Field(ge=0, le=7300)]
    international: bool
    new_device: bool
    merchant_category: Literal["retail", "grocery", "travel", "entertainment", "transfer"]


class Batch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transactions: Annotated[list[Transaction], Field(min_length=1, max_length=100)]


class Timings(BaseModel):
    preprocessing_ms: float
    inference_ms: float
    pipeline_ms: float


class Prediction(BaseModel):
    prediction: Literal["fraud", "legitimate"]
    risk_score: Annotated[float, Field(ge=0, le=1)]
    model_version: str
    dataset_kind: Literal["synthetic"]
    message: str
    indicators: list[str]


class PredictionResponse(BaseModel):
    result: Prediction
    timings: Timings


class BatchResponse(BaseModel):
    results: list[Prediction]
    timings: Timings
