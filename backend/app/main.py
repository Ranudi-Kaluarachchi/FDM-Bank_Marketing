import io
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .model_service import ModelNotReady, service
from .schemas import BatchResponse, ClientRecord, Prediction

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_BATCH_ROWS = 50_000


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        service.load()
    except ModelNotReady as exc:
        print(f"WARNING: {exc}")
    yield


app = FastAPI(
    title="Bank Marketing Term Deposit Predictor",
    description="Predicts whether a client will subscribe to a term deposit (UCI Bank Marketing dataset).",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_model() -> None:
    if not service.ready:
        raise HTTPException(status_code=503, detail="Model not loaded. Run `python -m ml.run_pipeline` first.")


@app.get("/api/health")
def health():
    return {"status": "ok", "model_loaded": service.ready,
            "model_name": service.metadata.get("model_name")}


@app.get("/api/metadata")
def metadata():
    _require_model()
    return service.metadata


@app.get("/api/metrics")
def metrics():
    _require_model()
    return service.metrics


@app.get("/api/insights")
def insights():
    _require_model()
    return {"insights": service.insights, "cleaning": service.cleaning}


@app.post("/api/predict", response_model=Prediction)
def predict(record: ClientRecord):
    _require_model()
    return service.predict([record.model_dump()])[0]


@app.post("/api/predict/batch", response_model=BatchResponse)
async def predict_batch(file: UploadFile = File(...)):
    _require_model()
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")
    try:
        df = pd.read_csv(io.BytesIO(content), sep=None, engine="python", dtype=str)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}")
    if df.empty:
        raise HTTPException(status_code=400, detail="CSV has no rows")
    if len(df) > MAX_BATCH_ROWS:
        raise HTTPException(status_code=413, detail=f"Too many rows (max {MAX_BATCH_ROWS})")

    df.columns = [c.strip().strip('"').lower() for c in df.columns]
    missing = [f for f in ClientRecord.model_fields if f not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing)}")

    valid_rows, valid_idx, errors = [], [], []
    for i, raw in enumerate(df[list(ClientRecord.model_fields)].to_dict(orient="records")):
        cleaned = {k: (v.strip().strip('"').lower() if isinstance(v, str) else v) for k, v in raw.items()}
        try:
            valid_rows.append(ClientRecord(**cleaned).model_dump())
            valid_idx.append(i)
        except ValidationError as exc:
            first = exc.errors()[0]
            field = ".".join(str(p) for p in first["loc"])
            errors.append({"row": i + 1, "error": f"{field}: {first['msg']}"})

    results = []
    if valid_rows:
        for i, row, pred in zip(valid_idx, valid_rows, service.predict(valid_rows)):
            results.append({"row": i + 1, **row, **pred})

    yes = sum(r["prediction"] == "yes" for r in results)
    return {
        "total": len(df),
        "predicted_yes": yes,
        "predicted_no": len(results) - yes,
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }
