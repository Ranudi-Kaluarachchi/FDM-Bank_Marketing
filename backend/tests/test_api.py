"""API tests. Run from the backend/ folder with:  pytest"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.model_service import MODEL_PATH

# Skip all tests if the model has not been trained yet.
pytestmark = pytest.mark.skipif(not MODEL_PATH.exists(), reason="run `python -m ml.run_pipeline` first")

# A valid client record reused by several tests.
SAMPLE = {
    "age": 35, "job": "management", "marital": "married", "education": "tertiary",
    "default": "no", "balance": 1500, "housing": "yes", "loan": "no",
    "contact": "cellular", "day": 15, "month": "may", "campaign": 2,
    "pdays": -1, "previous": 0, "poutcome": "unknown",
}


@pytest.fixture(scope="module")
def client():
    """In-process test client; the `with` block runs the app's start-up (model loading)."""
    with TestClient(app) as c:
        yield c


def test_health(client):
    """API is up and the model loaded."""
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["model_loaded"] is True


def test_metadata_and_metrics(client):
    """Metadata lists the categories, metrics cover all 6 models and agree on the selected one."""
    meta = client.get("/api/metadata").json()
    assert set(meta["features"]["categorical"]["job"]) >= {"management", "student"}
    metrics = client.get("/api/metrics").json()
    assert len(metrics["models"]) == 6
    assert metrics["best_model"] == meta["model_name"]


def test_insights(client):
    """EDA insights cover the full dataset and the cleaning report is present."""
    body = client.get("/api/insights").json()
    assert body["insights"]["rows"] > 40000
    assert body["cleaning"]["steps"]


def test_predict_single(client):
    """A valid record returns a score between 0 and 1 and a yes/no decision."""
    r = client.post("/api/predict", json=SAMPLE)
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["probability"] <= 1.0
    assert body["prediction"] in {"yes", "no"}


def test_previous_success_raises_probability(client):
    """Sanity check: a previous successful campaign should raise the score (strongest signal in EDA)."""
    base = client.post("/api/predict", json=SAMPLE).json()["probability"]
    success = {**SAMPLE, "poutcome": "success", "pdays": 90, "previous": 2, "month": "mar"}
    assert client.post("/api/predict", json=success).json()["probability"] > base


def test_predict_validation_error(client):
    """Out-of-range age and unknown job are rejected with HTTP 422."""
    r = client.post("/api/predict", json={**SAMPLE, "age": 5, "job": "astronaut"})
    assert r.status_code == 422


def test_batch(client):
    """Semicolon CSV with one good and one bad row: good row scored, bad row reported."""
    header = ";".join(SAMPLE.keys())
    good = ";".join(f'"{v}"' if isinstance(v, str) else str(v) for v in SAMPLE.values())
    bad = good.replace('"management"', '"astronaut"')
    csv = f"{header}\n{good}\n{bad}\n"
    r = client.post("/api/predict/batch", files={"file": ("clients.csv", csv, "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2 and body["failed"] == 1 and len(body["results"]) == 1
    assert body["errors"][0]["row"] == 2


def test_batch_missing_columns(client):
    """A CSV without the required columns is rejected with HTTP 400."""
    r = client.post("/api/predict/batch", files={"file": ("x.csv", "age,job\n30,student\n", "text/csv")})
    assert r.status_code == 400
