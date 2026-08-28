"""Non-leaky model helpers for ranking leads.

The high-value flag is derived from the compatibility score. Consequently the
score itself must never be fed back as a feature to predict that flag: doing so
would produce a misleadingly perfect model. This module uses only raw lead
attributes and labels the result as a prioritisation proxy.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

_CATEGORICAL_FEATURES = ["industry", "contact_title", "source"]
_NUMERIC_FEATURES = ["has_website", "has_email", "has_linkedin", "has_contact_name", "notes_length"]


class NotesCleaner(BaseEstimator, TransformerMixin):
    """Normalize arbitrary notes while preserving a token for missing notes."""

    def fit(self, X: pd.Series, y: pd.Series | None = None) -> "NotesCleaner":
        return self

    def transform(self, X: pd.Series) -> pd.Series:
        return pd.Series(X, copy=False).apply(self.clean_text)

    @staticmethod
    def clean_text(text: Any) -> str:
        if text is None or pd.isna(text):
            return "no_notes"
        cleaned = str(text).casefold()
        cleaned = re.sub(r"https?://\S+", " ", cleaned)
        cleaned = re.sub(r"\S+@\S+", " ", cleaned)
        cleaned = re.sub(r"[^\w\s]", " ", cleaned, flags=re.UNICODE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned or "no_notes"


class ConstantHighValueModel:
    """A safe fallback for datasets containing only one target class."""

    def __init__(self, probability: float) -> None:
        self.probability = float(probability)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        positive = np.full(len(X), self.probability, dtype=float)
        return np.column_stack((1.0 - positive, positive))


def _present(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().ne("").astype(int)


def make_model_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create features available before a compatibility score is assigned."""
    features = pd.DataFrame(index=df.index)
    for column in _CATEGORICAL_FEATURES:
        value = df.get(column, pd.Series("", index=df.index))
        features[column] = value.fillna("Non renseigné").astype(str).str.strip().replace("", "Non renseigné")

    notes = df.get("notes", pd.Series("", index=df.index)).fillna("").astype(str)
    features["notes"] = notes
    features["notes_length"] = notes.str.len().clip(upper=5_000)
    features["has_website"] = _present(df.get("website", pd.Series("", index=df.index)))
    features["has_email"] = (
        _present(df.get("contact_email", pd.Series("", index=df.index)))
        | _present(df.get("contact_email_personal", pd.Series("", index=df.index)))
    ).astype(int)
    features["has_linkedin"] = _present(df.get("contact_linkedin_url", pd.Series("", index=df.index)))
    features["has_contact_name"] = _present(df.get("contact_full_name", pd.Series("", index=df.index)))
    return features


def _sample_training_rows(df: pd.DataFrame, max_training_rows: int) -> pd.DataFrame:
    """Bound fitting time while retaining every target class in the sample."""
    if len(df) <= max_training_rows:
        return df
    labels = pd.to_numeric(df["high_value_flag"], errors="coerce").fillna(0).astype(int)
    fraction = max_training_rows / len(df)
    samples = []
    for _, group in df.groupby(labels, group_keys=False):
        size = min(len(group), max(1, round(len(group) * fraction)))
        samples.append(group.sample(n=size, random_state=42))
    return pd.concat(samples).sample(frac=1, random_state=42)


def build_high_value_model(df: pd.DataFrame, *, max_training_rows: int = 20_000):
    """Fit a prioritisation-proxy classifier, or a stable single-class fallback.

    Large uploads are sampled only for fitting. Every lead is still scored and
    ranked afterwards, keeping the interactive application responsive.
    """
    if df.empty:
        raise ValueError("Impossible d'entraîner un modèle sur un jeu de données vide.")
    if "high_value_flag" not in df:
        raise ValueError("La colonne `high_value_flag` est requise pour entraîner le modèle.")
    if max_training_rows < 2:
        raise ValueError("max_training_rows doit être supérieur ou égal à 2.")

    training_df = _sample_training_rows(df, max_training_rows)
    X = make_model_features(training_df)
    y = pd.to_numeric(training_df["high_value_flag"], errors="coerce").fillna(0).astype(int)
    if y.nunique() < 2:
        return ConstantHighValueModel(y.iloc[0])

    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), _CATEGORICAL_FEATURES),
            (
                "text",
                Pipeline(
                    [
                        ("cleaner", NotesCleaner()),
                        ("tfidf", TfidfVectorizer(max_features=750, ngram_range=(1, 2))),
                    ]
                ),
                "notes",
            ),
            ("numeric", "passthrough", _NUMERIC_FEATURES),
        ],
        sparse_threshold=0.3,
    )
    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", LogisticRegression(max_iter=1_000, class_weight="balanced", random_state=42)),
        ]
    )
    model.fit(X, y)
    return model


def predict_high_value(model: Any, df: pd.DataFrame) -> pd.DataFrame:
    """Append probability and flag without mutating the supplied DataFrame."""
    predicted = df.copy()
    probabilities = model.predict_proba(make_model_features(predicted))[:, 1]
    predicted["high_value_prob"] = probabilities
    predicted["predicted_high_value"] = (probabilities >= 0.5).astype(int)
    return predicted
