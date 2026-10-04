"""Shared paths and feature definitions for the Bank Marketing pipeline.

Every other module imports its file locations and column lists from here so
they are defined in exactly one place.
"""
from pathlib import Path

# ---- Folder layout (all relative to the repository root) -------------------
ROOT = Path(__file__).resolve().parent.parent   # repo root: ml/config.py -> ml -> root
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"                       # downloaded, untouched dataset
PROCESSED_DIR = DATA_DIR / "processed"           # cleaned dataset
ARTIFACTS_DIR = ROOT / "artifacts"               # model + JSON files used by the backend

# ---- Data files -------------------------------------------------------------
DATASET_URL = "https://archive.ics.uci.edu/static/public/222/bank+marketing.zip"
RAW_CSV = RAW_DIR / "bank-full.csv"              # 45,211 rows, semicolon separated
CLEAN_CSV = PROCESSED_DIR / "bank_clean.csv"

# ---- Artifacts produced by the pipeline and loaded by the backend -----------
MODEL_PATH = ARTIFACTS_DIR / "model.joblib"                 # trained scikit-learn pipeline
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"               # model comparison results
METADATA_PATH = ARTIFACTS_DIR / "metadata.json"             # input schema, defaults, threshold
INSIGHTS_PATH = ARTIFACTS_DIR / "insights.json"             # EDA aggregates for the dashboard
CLEANING_REPORT_PATH = ARTIFACTS_DIR / "cleaning_report.json"  # what data cleaning did

# ---- Modelling constants ----------------------------------------------------
TARGET = "y"          # did the client subscribe a term deposit? (1 = yes, 0 = no)
RANDOM_STATE = 42     # fixed seed so splits and models are reproducible

# Raw input fields a client record must provide (the API contract).
# `duration` is intentionally excluded: it is only known after the call ends
# and the dataset authors note it leaks the target.
NUMERIC_INPUTS = ["age", "balance", "day", "campaign", "pdays", "previous"]
CATEGORICAL_INPUTS = [
    "job", "marital", "education", "default", "housing",
    "loan", "contact", "month", "poutcome",
]
RAW_INPUTS = NUMERIC_INPUTS + CATEGORICAL_INPUTS

# Features produced by feature engineering (see transformers.FeatureEngineer).
ENGINEERED_NUMERIC = ["previously_contacted", "days_since_prev", "log_balance", "total_contacts"]
ENGINEERED_CATEGORICAL = ["age_group"]

# Columns that actually reach the model after feature engineering.
# `pdays` is replaced by `previously_contacted` + `days_since_prev`.
MODEL_NUMERIC = ["age", "balance", "day", "campaign", "previous"] + ENGINEERED_NUMERIC
MODEL_CATEGORICAL = CATEGORICAL_INPUTS + ENGINEERED_CATEGORICAL

# Calendar order of months (used for sorting charts and dropdowns).
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
