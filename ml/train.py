"""Train, tune and compare classifiers; persist the best pipeline and metrics.

Models: Logistic Regression, Decision Tree, Random Forest, Gradient Boosting
(HistGradientBoosting), K-Nearest Neighbours and Gaussian Naive Bayes.
The dataset is imbalanced (~12% positives), so models use class weighting
where supported, selection is by cross-validated ROC-AUC, and the decision
threshold of the winner is tuned for F1 on out-of-fold training predictions
(never on the test set).
"""
import json
import time
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, average_precision_score, confusion_matrix, f1_score,
    precision_recall_curve, precision_score, recall_score, roc_auc_score, roc_curve,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_predict, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.utils.class_weight import compute_sample_weight

from ml.config import (
    ARTIFACTS_DIR, CATEGORICAL_INPUTS, CLEAN_CSV, CLEANING_REPORT_PATH, METADATA_PATH,
    METRICS_PATH, MODEL_CATEGORICAL, MODEL_NUMERIC, MODEL_PATH, MONTHS, NUMERIC_INPUTS,
    RANDOM_STATE, RAW_INPUTS, TARGET,
)
from ml import report
from ml.transformers import FeatureEngineer, QuantileCapper


def build_pipeline(classifier) -> Pipeline:
    preprocessor = ColumnTransformer([
        ("num", Pipeline([("cap", QuantileCapper()), ("scale", StandardScaler())]), MODEL_NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), MODEL_CATEGORICAL),
    ])
    return Pipeline([
        ("features", FeatureEngineer()),
        ("preprocess", preprocessor),
        ("model", classifier),
    ])


def candidate_models() -> dict:
    rs = RANDOM_STATE
    return {
        "Logistic Regression": (
            LogisticRegression(max_iter=2000, class_weight="balanced"),
            {"model__C": [0.1, 1.0, 10.0]},
        ),
        "Decision Tree": (
            DecisionTreeClassifier(class_weight="balanced", random_state=rs),
            {"model__max_depth": [5, 8, 12], "model__min_samples_leaf": [20, 50]},
        ),
        "Random Forest": (
            RandomForestClassifier(n_estimators=300, class_weight="balanced_subsample",
                                   n_jobs=-1, random_state=rs),
            {"model__max_depth": [10, 16], "model__min_samples_leaf": [5, 10]},
        ),
        "Gradient Boosting": (
            HistGradientBoostingClassifier(random_state=rs),
            {"model__learning_rate": [0.05, 0.1], "model__max_depth": [4, 8]},
        ),
        "K-Nearest Neighbours": (
            KNeighborsClassifier(n_jobs=-1),
            {"model__n_neighbors": [25, 51], "model__weights": ["distance"]},
        ),
        "Naive Bayes": (GaussianNB(), {}),
    }


def needs_sample_weight(name: str) -> bool:
    return name == "Gradient Boosting"


def evaluate(y_true, proba, threshold: float = 0.5) -> dict:
    pred = (proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred).ravel()
    return {
        "threshold": round(float(threshold), 4),
        "accuracy": round(float(accuracy_score(y_true, pred)), 4),
        "precision": round(float(precision_score(y_true, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, pred)), 4),
        "f1": round(float(f1_score(y_true, pred)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, proba)), 4),
        "pr_auc": round(float(average_precision_score(y_true, proba)), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def roc_points(y_true, proba, n: int = 50) -> list[dict]:
    fpr, tpr, _ = roc_curve(y_true, proba)
    idx = np.unique(np.linspace(0, len(fpr) - 1, n).astype(int))
    return [{"fpr": round(float(fpr[i]), 4), "tpr": round(float(tpr[i]), 4)} for i in idx]


def best_f1_threshold(y_true, proba) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, proba)
    f1 = 2 * precision * recall / np.clip(precision + recall, 1e-12, None)
    return float(thresholds[int(np.argmax(f1[:-1]))])


def build_metadata(df: pd.DataFrame, best_name: str, threshold: float, metrics: dict) -> dict:
    numeric = {}
    for col in NUMERIC_INPUTS:
        s = df[col]
        numeric[col] = {"min": int(s.min()), "max": int(s.max()), "median": float(s.median())}
    categorical = {col: sorted(df[col].unique().tolist()) for col in CATEGORICAL_INPUTS}
    categorical["month"] = [m for m in MONTHS if m in categorical["month"]]
    defaults = {col: numeric[col]["median"] for col in NUMERIC_INPUTS}
    defaults.update({col: df[col].mode()[0] for col in CATEGORICAL_INPUTS})
    defaults["pdays"] = -1
    return {
        "model_name": best_name,
        "threshold": round(threshold, 4),
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "training_rows": int(len(df)),
        "test_metrics": metrics,
        "features": {"numeric": numeric, "categorical": categorical, "order": RAW_INPUTS},
        "defaults": {k: (int(v) if isinstance(v, float) and v.is_integer() else v) for k, v in defaults.items()},
    }


def run() -> dict:
    df = pd.read_csv(CLEAN_CSV)
    X, y = df[RAW_INPUTS], df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE)
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=RANDOM_STATE)
    train_weights = compute_sample_weight("balanced", y_train)

    results, fitted, test_probas = [], {}, {}
    for name, (clf, grid) in candidate_models().items():
        start = time.time()
        fit_params = {"model__sample_weight": train_weights} if needs_sample_weight(name) else {}
        search = GridSearchCV(build_pipeline(clf), grid or {"model__priors": [None]},
                              scoring="roc_auc", cv=cv, n_jobs=-1, refit=True)
        search.fit(X_train, y_train, **fit_params)
        proba = search.best_estimator_.predict_proba(X_test)[:, 1]
        res = {
            "name": name,
            "best_params": {k.replace("model__", ""): v for k, v in search.best_params_.items()},
            "cv_roc_auc": round(float(search.best_score_), 4),
            "train_seconds": round(time.time() - start, 1),
            "test": evaluate(y_test, proba),
            "roc_curve": roc_points(y_test, proba),
        }
        results.append(res)
        fitted[name] = search.best_estimator_
        test_probas[name] = proba
        print(f"{name:22s} CV AUC={res['cv_roc_auc']:.4f}  test AUC={res['test']['roc_auc']:.4f}  "
              f"F1={res['test']['f1']:.4f}  ({res['train_seconds']}s)")

    best = max(results, key=lambda r: r["cv_roc_auc"])
    best_name = best["name"]
    best_model = fitted[best_name]
    print(f"\nBest model by CV ROC-AUC: {best_name}")

    clf, _ = candidate_models()[best_name]
    tuned = build_pipeline(clf).set_params(**{f"model__{k}": v for k, v in best["best_params"].items()})
    oof_params = {"model__sample_weight": train_weights} if needs_sample_weight(best_name) else {}
    oof = cross_val_predict(tuned, X_train, y_train, cv=cv, method="predict_proba",
                            n_jobs=-1, params=oof_params)[:, 1]
    threshold = best_f1_threshold(y_train, oof)
    best_proba = best_model.predict_proba(X_test)[:, 1]
    tuned_metrics = evaluate(y_test, best_proba, threshold)
    print(f"Tuned threshold={threshold:.3f}  test F1={tuned_metrics['f1']:.4f}  "
          f"precision={tuned_metrics['precision']:.4f}  recall={tuned_metrics['recall']:.4f}")

    sample = X_test.sample(n=min(4000, len(X_test)), random_state=RANDOM_STATE)
    perm = permutation_importance(best_model, sample, y_test.loc[sample.index], scoring="roc_auc",
                                  n_repeats=5, random_state=RANDOM_STATE, n_jobs=-1)
    importance = sorted(
        [{"feature": f, "importance": round(float(m), 5), "std": round(float(s), 5)}
         for f, m, s in zip(RAW_INPUTS, perm.importances_mean, perm.importances_std)],
        key=lambda d: d["importance"], reverse=True)

    # Refit the winner on all clean data for deployment.
    final_params = {"model__sample_weight": compute_sample_weight("balanced", y)} if needs_sample_weight(best_name) else {}
    final_model = clone(tuned).fit(X, y, **final_params)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, MODEL_PATH)

    metrics = {
        "selection_metric": "cv_roc_auc",
        "best_model": best_name,
        "threshold": round(threshold, 4),
        "test_size": int(len(X_test)),
        "train_size": int(len(X_train)),
        "best_model_tuned_test": tuned_metrics,
        "feature_importance": importance,
        "models": results,
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))

    metadata = build_metadata(df, best_name, threshold, tuned_metrics)
    if CLEANING_REPORT_PATH.exists():
        metadata["cleaning"] = json.loads(CLEANING_REPORT_PATH.read_text())["steps"]
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))
    print(f"Saved model to {MODEL_PATH}")

    report.generate(metrics, y_test, test_probas, threshold)
    return metrics


if __name__ == "__main__":
    run()
