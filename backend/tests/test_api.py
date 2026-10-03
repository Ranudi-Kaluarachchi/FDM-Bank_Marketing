import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.model_service import MODEL_PATH

pytestmark = pytest.mark.skipif(not MODEL_PATH.exists(), reason="run `python -m ml.run_pipeline` first")

SAMPLE = {
    "age": 35, "job": "management", "marital": "married", "education": "tertiary",
    "default": "no", "balance": 1500, "housing": "yes", "loan": "no",
    "contact": "cellular", "day": 15, "month": "may", "campaign": 2,
    "pdays": -1, "previous": 0, "poutcome": "unknown",
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["model_loaded"] is True


def test_metadata_and_metrics(client):
    meta = client.get("/api/metadata").json()
    assert set(meta["features"]["categorical"]["job"]) >= {"management", "student"}
    metrics = client.get("/api/metrics").json()
    assert len(metrics["models"]) == 6
    assert metrics["best_model"] == meta["model_name"]


def test_insights(client):
    body = client.get("/api/insights").json()
    assert body["insights"]["rows"] > 40000
    assert body["cleaning"]["steps"]


def test_predict_single(client):
    r = client.post("/api/predict", json=SAMPLE)
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["probability"] <= 1.0
    assert body["prediction"] in {"yes", "no"}


def test_previous_success_raises_probability(client):
    base = client.post("/api/predict", json=SAMPLE).json()["probability"]
    success = {**SAMPLE, "poutcome": "success", "pdays": 90, "previous": 2, "month": "mar"}
    assert client.post("/api/predict", json=success).json()["probability"] > base


def test_predict_validation_error(client):
    r = client.post("/api/predict", json={**SAMPLE, "age": 5, "job": "astronaut"})
    assert r.status_code == 422


def test_batch(client):
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
    r = client.post("/api/predict/batch", files={"file": ("x.csv", "age,job\n30,student\n", "text/csv")})
    assert r.status_code == 400
