"""Data cleaning for the raw UCI bank-full.csv file.

Steps (each is recorded in artifacts/cleaning_report.json):
  1. Normalise column names and string values (trim, lowercase).
  2. Report missing values; impute if any appear (dataset ships with none,
     but 'unknown' placeholders are kept as an explicit category because they
     carry signal, e.g. contact='unknown' has a very low subscription rate).
  3. Remove exact duplicate rows.
  4. Validate domain rules (age range, day of month, month names, campaign>=1,
     pdays==-1 or >=0, binary fields) and drop violating rows.
  5. Drop `duration` (target leakage: only known after the call).
  6. Encode the target y as 0/1.
Outlier capping and encoding happen inside the model pipeline so they are
learned on training data only and applied identically at inference time.
"""
import json

import pandas as pd

from ml.config import (
    CATEGORICAL_INPUTS, CLEAN_CSV, CLEANING_REPORT_PATH, MONTHS, NUMERIC_INPUTS,
    PROCESSED_DIR, ARTIFACTS_DIR, RAW_CSV, TARGET,
)

BINARY_COLS = ["default", "housing", "loan", TARGET]


def load_raw() -> pd.DataFrame:
    if not RAW_CSV.exists():
        raise FileNotFoundError(f"{RAW_CSV} missing. Run `python -m ml.download_data` first.")
    return pd.read_csv(RAW_CSV, sep=";")


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report: dict = {"raw_rows": int(len(df)), "raw_columns": list(df.columns), "steps": []}

    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype(str).str.strip().str.lower()
    report["steps"].append({"step": "normalise_text", "detail": "Trimmed and lower-cased column names and string values"})

    missing = {c: int(n) for c, n in df.isna().sum().items() if n}
    for col in NUMERIC_INPUTS:
        if col in missing:
            df[col] = df[col].fillna(df[col].median())
    for col in CATEGORICAL_INPUTS:
        if col in missing:
            df[col] = df[col].fillna("unknown")
    df = df.dropna(subset=[TARGET])
    unknown_counts = {c: int((df[c] == "unknown").sum()) for c in CATEGORICAL_INPUTS if (df[c] == "unknown").any()}
    report["steps"].append({
        "step": "missing_values",
        "detail": "Median-impute numeric NaNs, 'unknown' for categorical NaNs; 'unknown' kept as a category",
        "nan_counts": missing,
        "unknown_counts": unknown_counts,
    })

    before = len(df)
    df = df.drop_duplicates()
    report["steps"].append({"step": "drop_duplicates", "rows_removed": int(before - len(df))})

    before = len(df)
    valid = (
        df["age"].between(18, 100)
        & df["day"].between(1, 31)
        & df["month"].isin(MONTHS)
        & (df["campaign"] >= 1)
        & ((df["pdays"] == -1) | (df["pdays"] >= 0))
        & (df["previous"] >= 0)
    )
    for col in BINARY_COLS:
        valid &= df[col].isin(["yes", "no"])
    df = df[valid]
    report["steps"].append({"step": "validate_domain_rules", "rows_removed": int(before - len(df))})

    if "duration" in df.columns:
        df = df.drop(columns=["duration"])
        report["steps"].append({"step": "drop_leakage_feature", "detail": "Removed `duration` (known only after the call)"})

    df[TARGET] = (df[TARGET] == "yes").astype(int)
    report["steps"].append({"step": "encode_target", "detail": "y: yes->1, no->0"})

    df = df.reset_index(drop=True)
    report["clean_rows"] = int(len(df))
    report["positive_rate"] = round(float(df[TARGET].mean()), 4)
    report["numeric_summary"] = df[NUMERIC_INPUTS].describe().round(2).to_dict()
    return df, report


def run() -> pd.DataFrame:
    df, report = clean(load_raw())
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN_CSV, index=False)
    CLEANING_REPORT_PATH.write_text(json.dumps(report, indent=2))
    print(f"Cleaned data: {report['raw_rows']} -> {report['clean_rows']} rows, "
          f"positive rate {report['positive_rate']:.2%}. Saved {CLEAN_CSV}")
    return df


if __name__ == "__main__":
    run()
