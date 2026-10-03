import json
import sys
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.config import (  # noqa: E402
    CLEANING_REPORT_PATH, INSIGHTS_PATH, METADATA_PATH, METRICS_PATH, MODEL_PATH, RAW_INPUTS,
)


class ModelNotReady(RuntimeError):
    pass


class ModelService:
    def __init__(self) -> None:
        self.model = None
        self.metadata: dict = {}
        self.metrics: dict = {}
        self.insights: dict = {}
        self.cleaning: dict = {}

    def load(self) -> None:
        if not MODEL_PATH.exists():
            raise ModelNotReady(
                f"Model artifact not found at {MODEL_PATH}. Run `python -m ml.run_pipeline` first.")
        self.model = joblib.load(MODEL_PATH)
        self.metadata = json.loads(METADATA_PATH.read_text())
        self.metrics = json.loads(METRICS_PATH.read_text())
        self.insights = json.loads(INSIGHTS_PATH.read_text()) if INSIGHTS_PATH.exists() else {}
        self.cleaning = json.loads(CLEANING_REPORT_PATH.read_text()) if CLEANING_REPORT_PATH.exists() else {}

    @property
    def ready(self) -> bool:
        return self.model is not None

    @property
    def threshold(self) -> float:
        return float(self.metadata.get("threshold", 0.5))

    def likelihood(self, p: float) -> str:
        if p >= self.threshold:
            return "high"
        if p >= self.threshold / 2:
            return "medium"
        return "low"

    def predict_proba(self, records: list[dict]) -> list[float]:
        if not self.ready:
            raise ModelNotReady("Model is not loaded")
        frame = pd.DataFrame(records, columns=RAW_INPUTS)
        return self.model.predict_proba(frame)[:, 1].tolist()

    def predict(self, records: list[dict]) -> list[dict]:
        out = []
        for p in self.predict_proba(records):
            out.append({
                "prediction": "yes" if p >= self.threshold else "no",
                "probability": round(p, 4),
                "threshold": round(self.threshold, 4),
                "likelihood": self.likelihood(p),
            })
        return out


service = ModelService()
