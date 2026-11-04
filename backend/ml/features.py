"""Hand-built cues used beside character n-grams in the desk classifier."""

from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

from services.framing import (
    CRITICAL_PATTERNS,
    GOV_ACTORS,
    NEGATIVE_NEAR,
    POSITIVE_NEAR,
    SUPPORTIVE_PATTERNS,
    _count_hits,
)


class LexiconFeatures(BaseEstimator, TransformerMixin):
    """Counts of framing cues. Kept importable so joblib can unpickle the model."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        rows = []
        for text in X:
            raw = text or ""
            devanagari = sum(1 for ch in raw if "\u0900" <= ch <= "\u097f")
            rows.append(
                [
                    _count_hits(raw, CRITICAL_PATTERNS),
                    _count_hits(raw, SUPPORTIVE_PATTERNS),
                    _count_hits(raw, GOV_ACTORS),
                    _count_hits(raw, POSITIVE_NEAR),
                    _count_hits(raw, NEGATIVE_NEAR),
                    devanagari / max(len(raw), 1),
                ]
            )
        return np.asarray(rows, dtype=float)
