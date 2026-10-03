"""Shared paths and feature definitions for the Bank Marketing pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
ARTIFACTS_DIR = ROOT / "artifacts"

DATASET_URL = "https://archive.ics.uci.edu/static/public/222/bank+marketing.zip"
RAW_CSV = RAW_DIR / "bank-full.csv"
CLEAN_CSV = PROCESSED_DIR / "bank_clean.csv"

MODEL_PATH = ARTIFACTS_DIR / "model.joblib"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"
METADATA_PATH = ARTIFACTS_DIR / "metadata.json"
INSIGHTS_PATH = ARTIFACTS_DIR / "insights.json"
CLEANING_REPORT_PATH = ARTIFACTS_DIR / "cleaning_report.json"

TARGET = "y"
RANDOM_STATE = 42

# Raw input fields a client record must provide (the API contract).
# `duration` is intentionally excluded: it is only known after the call ends
# and the dataset authors note it leaks the target.
NUMERIC_INPUTS = ["age", "balance", "day", "campaign", "pdays", "previous"]
CATEGORICAL_INPUTS = [
    "job", "marital", "education", "default", "housing",
    "loan", "contact", "month", "poutcome",
]
RAW_INPUTS = NUMERIC_INPUTS + CATEGORICAL_INPUTS

# Features produced by feature engineering (see preprocess.engineer_features).
ENGINEERED_NUMERIC = ["previously_contacted", "days_since_prev", "log_balance", "total_contacts"]
ENGINEERED_CATEGORICAL = ["age_group"]

MODEL_NUMERIC = ["age", "balance", "day", "campaign", "previous"] + ENGINEERED_NUMERIC
MODEL_CATEGORICAL = CATEGORICAL_INPUTS + ENGINEERED_CATEGORICAL

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
