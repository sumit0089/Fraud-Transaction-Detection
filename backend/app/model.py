import time
from pathlib import Path
import joblib
import pandas as pd
import sklearn
from backend.app.schema import FEATURES


class ModelService:
    def __init__(self, directory):
        # Only load trusted, locally generated artifacts: joblib can execute code.
        artifact = joblib.load(Path(directory) / "model.joblib")
        self.pipeline = artifact["pipeline"]
        self.metadata = artifact["metadata"]
        if self.metadata["features"] != FEATURES or list(self.pipeline.feature_names_in_) != FEATURES:
            raise ValueError("Model feature schema mismatch")
        if self.metadata["sklearn_version"] != sklearn.__version__:
            raise ValueError("Model runtime version mismatch; retrain with installed dependencies")
        if list(self.pipeline.classes_) != [0, 1] or self.metadata["dataset_kind"] != "synthetic":
            raise ValueError("Unsupported model class contract")
        self.preprocessor = self.pipeline.named_steps["preprocessing"]
        self.classifier = self.pipeline.named_steps["classifier"]

    def predict(self, transactions):
        start = time.perf_counter()
        frame = pd.DataFrame([t.model_dump() for t in transactions], columns=FEATURES)
        transformed = self.preprocessor.transform(frame)
        preprocessed = time.perf_counter()
        scores = self.classifier.predict_proba(transformed)[:, 1]
        inferred = time.perf_counter()
        results = []
        for tx, score in zip(transactions, scores):
            flagged = bool(score >= self.metadata["threshold"])
            indicators = []
            if tx.new_device:
                indicators.append("Transaction uses a new device.")
            if tx.international:
                indicators.append("Transaction is marked international.")
            if tx.transactions_24h >= 10:
                indicators.append("At least 10 transactions reported within 24 hours.")
            results.append({"prediction": "fraud" if flagged else "legitimate", "risk_score": float(score),
                            "model_version": self.metadata["model_version"], "dataset_kind": "synthetic",
                            "message": "High-risk alert: review this synthetic transaction." if flagged else "Below the model's review threshold; this does not guarantee safety.",
                            "indicators": indicators})
        return {"results": results, "timings": {"preprocessing_ms": (preprocessed-start)*1000,
                "inference_ms": (inferred-preprocessed)*1000, "pipeline_ms": (time.perf_counter()-start)*1000}}
