"""End-to-end pipeline: download -> clean -> EDA -> train.

Run with:  python -m ml.run_pipeline
"""
from ml import download_data, eda, preprocess, train


def main() -> None:
    download_data.download()  # 1. fetch bank-full.csv from UCI (skipped if already downloaded)
    preprocess.run()          # 2. clean the data -> data/processed/bank_clean.csv
    eda.run()                 # 3. exploratory statistics -> artifacts/insights.json
    train.run()               # 4. train/compare models -> artifacts/ + reports/


if __name__ == "__main__":
    main()
