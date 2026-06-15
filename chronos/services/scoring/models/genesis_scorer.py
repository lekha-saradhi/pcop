"""GENESIS — Logistic Regression cold-start scorer with graduation logic."""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

GRADUATION_TENURE_DAYS = 90
GRADUATION_MIN_TOKENS = 30

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MODEL_PATH = ROOT / "ml" / "checkpoints" / "genesis_lr.pkl"


class GENESISScorer:
    """Logistic Regression cold-start fallback scorer."""

    MODEL_VERSION = "genesis-v1.0"

    def __init__(self, model_path: str | Path = DEFAULT_MODEL_PATH) -> None:
        self._model_path = Path(model_path)
        self._model: LogisticRegression | None = None
        self._feature_names: list[str] | None = None

    def load(self) -> None:
        """Load the serialized LogisticRegression model."""
        if not self._model_path.exists():
            raise FileNotFoundError(f"GENESIS model not found at {self._model_path}")
        with open(self._model_path, "rb") as f:
            saved = pickle.load(f)
        self._model = saved["model"]
        self._feature_names = saved["feature_names"]
        logger.info("GENESIS model loaded from %s", self._model_path)

    def score(self, features: dict[str, float]) -> float:
        """Return churn probability for a cold-start customer.

        Args:
            features: 7 cold-start features from cold_start_features.py.

        Returns:
            Churn probability in [0, 1].
        """
        if self._model is None:
            self.load()
        assert self._model is not None
        assert self._feature_names is not None

        x = np.array([[features[f] for f in self._feature_names]])
        return float(self._model.predict_proba(x)[0, 1])

    def reason_codes(self, features: dict[str, float], top_k: int = 3) -> list[dict[str, Any]]:
        """Return top-k coefficient-based reason codes.

        Args:
            features: Cold-start feature dict.
            top_k: Number of reason codes.

        Returns:
            List of dicts with 'feature', 'coefficient', 'direction'.
        """
        if self._model is None:
            self.load()
        assert self._model is not None
        assert self._feature_names is not None

        coefs = self._model.coef_[0]
        feature_values = np.array([features[f] for f in self._feature_names])
        contributions = coefs * feature_values

        indices = np.argsort(np.abs(contributions))[-top_k:][::-1]
        return [
            {
                "feature": self._feature_names[i],
                "coefficient": float(coefs[i]),
                "direction": "increases_risk" if contributions[i] > 0 else "decreases_risk",
            }
            for i in indices
        ]

    def is_graduated(self, tenure_days: int, token_count: int) -> bool:
        """Check if customer has graduated beyond cold-start threshold.

        Args:
            tenure_days: Days since account open.
            token_count: Number of non-PAD tokens in the customer's sequence.

        Returns:
            True if customer should be re-scored via TARE+HABITAT.
        """
        return tenure_days >= GRADUATION_TENURE_DAYS and token_count >= GRADUATION_MIN_TOKENS
