"""Loads the trained model and its JSON artifacts, and turns client records into predictions."""
import json
import sys
from pathlib import Path

import joblib
import pandas as pd

# Make the repository root importable so `ml.*` modules can be found. This is
# required because the saved pipeline references ml.transformers classes, which
# must be importable when joblib unpickles it.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.config import (  # noqa: E402
    CLEANING_REPORT_PATH, INSIGHTS_PATH, METADATA_PATH, METRICS_PATH, MODEL_PATH, RAW_INPUTS,
)


class ModelNotReady(RuntimeError):
    """Raised when artifacts are missing (the training pipeline has not been run yet)."""


class ModelService:
    """Holds the model and artifacts in memory for the lifetime of the API process."""

    def __init__(self) -> None:
        self.model = None           # scikit-learn pipeline (feature engineering + preprocessing + classifier)
        self.metadata: dict = {}    # input schema, defaults, threshold
        self.metrics: dict = {}     # model comparison results
        self.insights: dict = {}    # EDA aggregates
        self.cleaning: dict = {}    # data-cleaning report

    def load(self) -> None:
        """Read all artifacts from disk. Called once at API start-up."""
        if not MODEL_PATH.exists():
            raise ModelNotReady(
                f"Model artifact not found at {MODEL_PATH}. Run `python -m ml.run_pipeline` first.")
        self.model = joblib.load(MODEL_PATH)
        self.metadata = json.loads(METADATA_PATH.read_text())
        self.metrics = json.loads(METRICS_PATH.read_text())
        # EDA and cleaning reports are optional; the API still predicts without them.
        self.insights = json.loads(INSIGHTS_PATH.read_text()) if INSIGHTS_PATH.exists() else {}
        self.cleaning = json.loads(CLEANING_REPORT_PATH.read_text()) if CLEANING_REPORT_PATH.exists() else {}

    @property
    def ready(self) -> bool:
        """True once the model has been loaded."""
        return self.model is not None

    @property
    def threshold(self) -> float:
        """Decision threshold tuned during training (score >= threshold -> 'yes')."""
        return float(self.metadata.get("threshold", 0.5))

    def likelihood(self, p: float) -> str:
        """Lead priority band: high = above threshold, medium = at least half of it, otherwise low."""
        if p >= self.threshold:
            return "high"
        if p >= self.threshold / 2:
            return "medium"
        return "low"

    def predict_proba(self, records: list[dict]) -> list[float]:
        """Subscription score (0-1) for each raw client record."""
        if not self.ready:
            raise ModelNotReady("Model is not loaded")
        # Columns are put in the exact order used during training.
        frame = pd.DataFrame(records, columns=RAW_INPUTS)
        return self.model.predict_proba(frame)[:, 1].tolist()  # column 1 = probability of "yes"

    def predict(self, records: list[dict]) -> list[dict]:
        """Full prediction for each record: yes/no decision, score, threshold and lead priority."""
        out = []
        for p in self.predict_proba(records):
            out.append({
                "prediction": "yes" if p >= self.threshold else "no",
                "probability": round(p, 4),
                "threshold": round(self.threshold, 4),
                "likelihood": self.likelihood(p),
            })
        return out


# Single shared instance used by the API routes.
service = ModelService()
