"""Custom scikit-learn transformers used inside the saved model pipeline.

They live in an importable module so the backend can unpickle the pipeline.
"""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

# Age bands used for the engineered `age_group` feature and the EDA charts.
AGE_BINS = [0, 25, 35, 45, 55, 65, 200]
AGE_LABELS = ["18-25", "26-35", "36-45", "46-55", "56-65", "65+"]


def age_group(age: pd.Series) -> pd.Series:
    """Map numeric ages to the labelled bands above (e.g. 30 -> '26-35')."""
    return pd.cut(age, bins=AGE_BINS, labels=AGE_LABELS, right=True).astype(str)


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """Derive model features from raw client fields (stateless).

    Adds:
      previously_contacted  1 if the client was contacted in an earlier campaign (pdays != -1)
      days_since_prev       days since that contact, 0 if never contacted
      log_balance           signed log of balance, which tames its very long tail
      total_contacts        contacts in this campaign + previous campaigns
      age_group             age band (categorical)
    and drops `pdays`, whose -1 "never contacted" code would mislead numeric models.
    """

    def fit(self, X, y=None):
        # Nothing to learn: every feature is a fixed formula of the inputs.
        return self

    def transform(self, X):
        X = X.copy()  # never modify the caller's DataFrame
        pdays = X["pdays"].astype(float)
        contacted = pdays >= 0
        X["previously_contacted"] = contacted.astype(int)
        X["days_since_prev"] = np.where(contacted, pdays, 0.0)
        balance = X["balance"].astype(float)
        # sign(b) * log(1 + |b|) keeps negative balances negative while compressing large values.
        X["log_balance"] = np.sign(balance) * np.log1p(np.abs(balance))
        X["total_contacts"] = X["campaign"].astype(float) + X["previous"].astype(float)
        X["age_group"] = age_group(X["age"].astype(float))
        return X.drop(columns=["pdays"])


class QuantileCapper(BaseEstimator, TransformerMixin):
    """Winsorise numeric columns to quantiles learned on the training data.

    Values below the `lower` quantile or above the `upper` quantile are clipped
    to those limits, which reduces the influence of extreme outliers (e.g. very
    large balances or 60 calls in a campaign) without deleting rows.
    """

    def __init__(self, lower: float = 0.01, upper: float = 0.99):
        self.lower = lower
        self.upper = upper

    def fit(self, X, y=None):
        # Learn the clipping limits per column from the training data only.
        arr = np.asarray(X, dtype=float)
        self.lower_ = np.nanquantile(arr, self.lower, axis=0)
        self.upper_ = np.nanquantile(arr, self.upper, axis=0)
        self.n_features_in_ = arr.shape[1]
        return self

    def transform(self, X):
        # Apply the same limits to training, test and live API data.
        return np.clip(np.asarray(X, dtype=float), self.lower_, self.upper_)

    def get_feature_names_out(self, input_features=None):
        # Column names are unchanged; needed so scikit-learn can track feature names.
        return np.asarray(input_features, dtype=object)
