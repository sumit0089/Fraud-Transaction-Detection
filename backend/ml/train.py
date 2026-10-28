"""Offline training only. Deterministic synthetic generator; never bank data."""
import argparse
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from backend.app.schema import CATEGORIES, FEATURES, NUMERIC

ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts"


def generate_data(rows=16000, seed=42):
    rng = np.random.default_rng(seed)
    data = pd.DataFrame({
        "amount": np.clip(rng.lognormal(4.5, 1.4, rows), .01, 1_000_000),
        "hour": rng.integers(0, 24, rows),
        "transactions_24h": np.clip(1 + rng.poisson(3, rows), 1, 100),
        "distance_km": np.clip(rng.exponential(80, rows), 0, 20_000),
        "account_age_days": rng.integers(0, 7301, rows),
        "international": rng.random(rows) < .12,
        "new_device": rng.random(rows) < .15,
        "merchant_category": rng.choice(CATEGORIES, rows, p=[.3, .25, .1, .15, .2]),
    })[FEATURES]
    # Stochastic labels create overlapping classes, not deterministic UI rules.
    logit = (-5.3 + .0015 * data.amount + .004 * data.distance_km
             + .32 * data.transactions_24h + 1.1 * data.international
             + 1.4 * data.new_device + .8 * (data.hour < 5)
             + .8 * (data.account_age_days < 90)
             + .5 * (data.merchant_category == "transfer"))
    labels = rng.binomial(1, 1 / (1 + np.exp(-np.clip(logit, -30, 30))))
    return data, labels


def train(output_dir=ARTIFACT_DIR, rows=16000):
    data, labels = generate_data(rows)
    x_train, x_hold, y_train, y_hold = train_test_split(data, labels, test_size=.4, stratify=labels, random_state=42)
    x_val, x_test, y_val, y_test = train_test_split(x_hold, y_hold, test_size=.5, stratify=y_hold, random_state=43)
    preprocessing = ColumnTransformer([
        ("numeric", StandardScaler(), NUMERIC),
        ("binary", "passthrough", ["international", "new_device"]),
        ("category", OneHotEncoder(categories=[CATEGORIES], handle_unknown="error", sparse_output=False), ["merchant_category"]),
    ], remainder="drop")
    pipeline = Pipeline([("preprocessing", preprocessing), ("classifier", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42))])
    pipeline.fit(x_train, y_train)
    # Select threshold only on validation. Test remains untouched until final evaluation.
    val_scores = pipeline.predict_proba(x_val)[:, 1]
    candidates = np.linspace(.1, .9, 81)
    threshold = float(max(candidates, key=lambda t: f1_score(y_val, val_scores >= t)))
    scores = pipeline.predict_proba(x_test)[:, 1]
    predicted = scores >= threshold
    fingerprint = hashlib.sha256(pd.util.hash_pandas_object(data, index=True).values.tobytes() + labels.tobytes()).hexdigest()[:12]
    metadata = {
        "model_version": f"synthetic-logreg-v1-{fingerprint}",
        "dataset_kind": "synthetic", "dataset_source": "backend/ml/train.py:generate_data (seed 42)",
        "rows": rows, "fraud_fraction": float(labels.mean()),
        "split": {"train": len(x_train), "validation": len(x_val), "test": len(x_test)},
        "features": FEATURES, "threshold": threshold, "sklearn_version": sklearn.__version__,
        "metrics": {"precision": precision_score(y_test, predicted, zero_division=0), "recall": recall_score(y_test, predicted),
                    "f1": f1_score(y_test, predicted), "roc_auc": roc_auc_score(y_test, scores),
                    "average_precision": average_precision_score(y_test, scores),
                    "confusion_matrix": confusion_matrix(y_test, predicted, labels=[0, 1]).tolist()},
        "limitations": ["Synthetic data only; not validated on real financial transactions.",
                         "Class-weighted probabilities are not calibrated real-world fraud probabilities.",
                         "Indicators describe input conditions, not causal explanations.",
                         "Random stratified splits measure this simulator, not temporal generalization."],
    }
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipeline, "metadata": metadata}, output_dir / "model.joblib")
    (output_dir / "metrics.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=16000)
    args = parser.parse_args()
    print(json.dumps(train(rows=args.rows), indent=2))
