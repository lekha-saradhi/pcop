"""HABITAT Pass 1 — XGBoost tabular churn scorer with SHAP reason codes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import xgboost as xgb

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MODEL_PATH = ROOT / "ml" / "checkpoints" / "habitat_pass1.json"

# Hyperparameters from spec
XGBOOST_PARAMS: dict[str, Any] = {
    "max_depth": 6,
    "eta": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "scale_pos_weight": 5.5,
    "objective": "binary:logistic",
    "eval_metric": ["auc", "logloss"],
    "seed": 42,
    "nthread": -1,
}


class HABITATScorer:
    """XGBoost-based tabular churn scorer (Pass 1)."""

    def __init__(self, model_path: str | Path = DEFAULT_MODEL_PATH) -> None:
        self._model: xgb.Booster | None = None
        self._model_path = Path(model_path)
        self._feature_names: list[str] | None = None

    def load(self) -> None:
        """Load the XGBoost model from its JSON file."""
        if not self._model_path.exists():
            raise FileNotFoundError(f"HABITAT model not found at {self._model_path}")
        self._model = xgb.Booster()
        self._model.load_model(str(self._model_path))
        self._feature_names = self._model.feature_names
        logger.info("HABITAT Pass 1 model loaded from %s", self._model_path)

    def score(self, features: dict[str, float]) -> float:
        """Score a single customer.

        Args:
            features: Dict of 14 Pass 1 features from tabular_features.py.

        Returns:
            Churn probability in [0, 1].
        """
        if self._model is None:
            self.load()
        assert self._model is not None

        feature_array = np.array([[features[f] for f in self._feature_names]], dtype=np.float32)
        dmatrix = xgb.DMatrix(feature_array, feature_names=self._feature_names)
        prob = float(self._model.predict(dmatrix)[0])
        return prob

    def score_batch(self, features_list: list[dict[str, float]]) -> np.ndarray:
        """Score a batch of customers.

        Args:
            features_list: List of feature dicts.

        Returns:
            np.ndarray of shape (n,) with churn probabilities.
        """
        if self._model is None:
            self.load()
        assert self._model is not None

        data = np.array([[f[fn] for fn in self._feature_names] for f in features_list], dtype=np.float32)
        dmatrix = xgb.DMatrix(data, feature_names=self._feature_names)
        return self._model.predict(dmatrix)

    def shap_reason_codes(self, features: dict[str, float], top_k: int = 3) -> list[dict[str, Any]]:
        """Compute SHAP values and return top-k reason codes.

        Args:
            features: Pass 1 feature dict.
            top_k: Number of reason codes to return.

        Returns:
            List of dicts with 'feature', 'shap_value', 'direction' keys.
        """
        import shap

        if self._model is None:
            self.load()
        assert self._model is not None

        feature_array = np.array([[features[f] for f in self._feature_names]], dtype=np.float32)
        explainer = shap.TreeExplainer(self._model)
        shap_values = explainer.shap_values(feature_array)[0]

        indices = np.argsort(np.abs(shap_values))[-top_k:][::-1]
        codes = []
        for i in indices:
            fname = self._feature_names[i]
            sv = float(shap_values[i])
            codes.append({
                "feature": fname,
                "shap_value": sv,
                "direction": "increases_risk" if sv > 0 else "decreases_risk",
            })
        return codes
