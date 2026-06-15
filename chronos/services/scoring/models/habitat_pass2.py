"""HABITAT Pass 2 — re-scorer using life event features from Layer 4."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

PASS2_TRIGGER_SCORE = 0.35
PASS2_MIN_LIFE_EVENTS = 1

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PASS1_PATH = ROOT / "ml" / "checkpoints" / "habitat_pass1.json"
DEFAULT_PASS2_PATH = ROOT / "ml" / "checkpoints" / "habitat_pass2.json"


def is_eligible_for_pass2(pass1_score: float, life_event_count: int) -> bool:
    """Return True if customer qualifies for Pass 2 re-scoring.

    Args:
        pass1_score: Output from HABITAT Pass 1.
        life_event_count: Number of life events detected by Layer 4.
    """
    return pass1_score >= PASS2_TRIGGER_SCORE and life_event_count >= PASS2_MIN_LIFE_EVENTS


def merge_life_event_features(
    pass1_features: dict[str, float],
    life_events: list[dict[str, Any]],
) -> dict[str, float]:
    """Merge Pass 1 features with life event features for Pass 2 model input.

    Args:
        pass1_features: 14-feature dict from tabular_features.extract_pass1_features.
        life_events: List of life event dicts from Layer 4.

    Returns:
        23-feature dict (14 Pass 1 + 9 life event features).
    """
    from ml.features.tabular_features import PASS2_LIFE_EVENT_FEATURES

    event_types = {e["event_type"] for e in life_events}
    life_feature_map = {
        "life_event_income_change": float("income_change" in event_types),
        "life_event_address_change": float("address_change" in event_types),
        "life_event_employer_change": float("employer_change" in event_types),
        "life_event_marriage": float("marriage" in event_types),
        "life_event_new_child": float("new_child" in event_types),
        "life_event_competitor_app": float("competitor_app" in event_types),
        "life_event_large_withdrawal": float("large_withdrawal" in event_types),
        "life_event_fd_break": float("fd_break" in event_types),
        "life_event_count": float(len(life_events)),
    }
    return {**pass1_features, **life_feature_map}


class HabitatPass2Scorer:
    """HABITAT Pass 2 re-scorer (weekly retrain once production data is available)."""

    MODEL_VERSION = "habitat-p2-v1.0"

    def __init__(
        self,
        pass1_model_path: str | Path = DEFAULT_PASS1_PATH,
        pass2_model_path: str | Path = DEFAULT_PASS2_PATH,
    ) -> None:
        self._pass1_path = Path(pass1_model_path)
        self._pass2_path = Path(pass2_model_path)
        self._pass2_model = None

    def _load_pass2(self) -> None:
        import xgboost as xgb

        if not self._pass2_path.exists():
            # TODO(#issue-XXX): Train Pass 2 model once production data is available (week 8+)
            logger.warning("Pass 2 model not found at %s — Pass 2 disabled", self._pass2_path)
            return
        self._pass2_model = xgb.Booster()
        self._pass2_model.load_model(str(self._pass2_path))
        logger.info("HABITAT Pass 2 model loaded from %s", self._pass2_path)

    def run_conditional(
        self,
        customer_id: str,
        pass1_score: float,
        pass1_features: dict[str, float],
        life_events: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Run Pass 2 if eligible; return score override dict or None.

        Args:
            customer_id: Customer identifier.
            pass1_score: Pass 1 churn probability.
            pass1_features: 14 Pass 1 features.
            life_events: Layer 4 life events for this customer.

        Returns:
            Dict with 'pass2_score', 'model_version', 'merged_features' if eligible.
            None if not eligible or Pass 2 model not available.
        """
        if not is_eligible_for_pass2(pass1_score, len(life_events)):
            logger.debug("customer_id=%s: not eligible for Pass 2", customer_id)
            return None

        if self._pass2_model is None:
            self._load_pass2()
        if self._pass2_model is None:
            logger.warning("customer_id=%s: Pass 2 skipped (model unavailable)", customer_id)
            return None

        import xgboost as xgb

        merged = merge_life_event_features(pass1_features, life_events)
        feature_names = self._pass2_model.feature_names
        data = np.array([[merged[f] for f in feature_names]], dtype=np.float32)
        dmatrix = xgb.DMatrix(data, feature_names=feature_names)
        pass2_score = float(self._pass2_model.predict(dmatrix)[0])

        logger.info(
            "customer_id=%s: Pass2 score=%.4f (was %.4f)", customer_id, pass2_score, pass1_score
        )
        return {
            "pass2_score": pass2_score,
            "model_version": self.MODEL_VERSION,
            "merged_features": merged,
        }
