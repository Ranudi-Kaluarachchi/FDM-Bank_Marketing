"""Custom scikit-learn transformers used inside the saved model pipeline.

They live in an importable module so the backend can unpickle the pipeline.
"""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

AGE_BINS = [0, 25, 35, 45, 55, 65, 200]
AGE_LABELS = ["18-25", "26-35", "36-45", "46-55", "56-65", "65+"]


def age_group(age: pd.Series) -> pd.Series:
    return pd.cut(age, bins=AGE_BINS, labels=AGE_LABELS, right=True).astype(str)


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """Derive model features from raw client fields (stateless)."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X.copy()
        pdays = X["pdays"].astype(float)
        contacted = pdays >= 0
        X["previously_contacted"] = contacted.astype(int)
        X["days_since_prev"] = np.where(contacted, pdays, 0.0)
        balance = X["balance"].astype(float)
        X["log_balance"] = np.sign(balance) * np.log1p(np.abs(balance))
        X["total_contacts"] = X["campaign"].astype(float) + X["previous"].astype(float)
        X["age_group"] = age_group(X["age"].astype(float))
        return X.drop(columns=["pdays"])


class QuantileCapper(BaseEstimator, TransformerMixin):
    """Winsorise numeric columns to quantiles learned on the training data."""

    def __init__(self, lower: float = 0.01, upper: float = 0.99):
        self.lower = lower
        self.upper = upper

    def fit(self, X, y=None):
        arr = np.asarray(X, dtype=float)
        self.lower_ = np.nanquantile(arr, self.lower, axis=0)
        self.upper_ = np.nanquantile(arr, self.upper, axis=0)
        self.n_features_in_ = arr.shape[1]
        return self

    def transform(self, X):
        return np.clip(np.asarray(X, dtype=float), self.lower_, self.upper_)

    def get_feature_names_out(self, input_features=None):
        return np.asarray(input_features, dtype=object)
