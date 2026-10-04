"""Exploratory data analysis: writes aggregated insights for the dashboard.

Produces artifacts/insights.json with class balance, subscription rate per
category, an age histogram, the effect of call count and numeric correlations.

Run with:  python -m ml.eda
"""
import json

import numpy as np
import pandas as pd

from ml.config import CLEAN_CSV, INSIGHTS_PATH, MONTHS, TARGET
from ml.transformers import AGE_LABELS, age_group


def _rate_by(df: pd.DataFrame, col: str, order: list[str] | None = None) -> list[dict]:
    """Subscription rate and row count for each value of `col`.

    If `order` is given (e.g. calendar months) rows follow that order;
    otherwise they are sorted from highest to lowest subscription rate.
    """
    # mean of a 0/1 target = share of clients who subscribed
    g = df.groupby(col, observed=True)[TARGET].agg(["count", "mean"]).reset_index()
    if order:
        g[col] = pd.Categorical(g[col], categories=order, ordered=True)
        g = g.sort_values(col)
    else:
        g = g.sort_values("mean", ascending=False)
    return [
        {"category": str(r[col]), "count": int(r["count"]), "rate": round(float(r["mean"]), 4)}
        for _, r in g.iterrows()
    ]


def _histogram(series: pd.Series, y: pd.Series, bins: np.ndarray) -> list[dict]:
    """Count subscribers ('yes') and non-subscribers ('no') in each bin of a numeric column."""
    out = []
    cats = pd.cut(series, bins=bins, include_lowest=True)
    grouped = pd.DataFrame({"bin": cats, "y": y}).groupby("bin", observed=False)["y"]
    for interval, grp in grouped:
        out.append({
            "bin": f"{int(interval.left)}-{int(interval.right)}",
            "no": int((grp == 0).sum()),
            "yes": int((grp == 1).sum()),
        })
    return out


def build_insights(df: pd.DataFrame) -> dict:
    """Compute every EDA aggregate shown on the dashboard's Data insights tab."""
    df = df.copy()
    # Helper columns used only for analysis.
    df["age_group"] = age_group(df["age"])
    df["previously_contacted"] = np.where(df["pdays"] >= 0, "yes", "no")

    # Pearson correlation between each numeric column and the 0/1 target.
    numeric = ["age", "balance", "day", "campaign", "pdays", "previous"]
    corr = df[numeric + [TARGET]].corr()[TARGET].drop(TARGET)

    # Group campaign call counts as 1..9 and "10+" (very few clients get more than 10 calls).
    campaign_bucket = df["campaign"].clip(upper=10).astype(int).astype(str).replace("10", "10+")

    return {
        "rows": int(len(df)),
        "class_balance": {
            "no": int((df[TARGET] == 0).sum()),
            "yes": int((df[TARGET] == 1).sum()),
            "positive_rate": round(float(df[TARGET].mean()), 4),
        },
        "rate_by": {
            "job": _rate_by(df, "job"),
            "marital": _rate_by(df, "marital"),
            "education": _rate_by(df, "education"),
            "contact": _rate_by(df, "contact"),
            "poutcome": _rate_by(df, "poutcome"),
            "housing": _rate_by(df, "housing"),
            "loan": _rate_by(df, "loan"),
            "month": _rate_by(df, "month", MONTHS),
            "age_group": _rate_by(df, "age_group", AGE_LABELS),
            "previously_contacted": _rate_by(df, "previously_contacted"),
        },
        "age_histogram": _histogram(df["age"], df[TARGET], np.arange(15, 100, 5)),  # 5-year bins
        "campaign_rate": _rate_by(df.assign(campaign_bucket=campaign_bucket),
                                  "campaign_bucket", [str(i) for i in range(1, 10)] + ["10+"]),
        "numeric_correlation_with_target": {k: round(float(v), 4) for k, v in corr.items()},
        "numeric_summary": df[numeric].describe().round(2).to_dict(),
    }


def run() -> dict:
    """Load the clean data, compute insights and save them as JSON."""
    df = pd.read_csv(CLEAN_CSV)
    insights = build_insights(df)
    INSIGHTS_PATH.write_text(json.dumps(insights, indent=2))
    print(f"Saved EDA insights to {INSIGHTS_PATH}")
    return insights


if __name__ == "__main__":
    run()
