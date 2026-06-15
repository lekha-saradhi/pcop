"""Platt scaling calibration utilities for CHRONOS model outputs."""

from __future__ import annotations

import logging
from typing import Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression

logger = logging.getLogger(__name__)


class PlattCalibrator:
    """Platt scaling: fit sigmoid on model outputs and calibrate probabilities."""

    def __init__(self) -> None:
        self._lr: LogisticRegression | None = None
        self._a: float = 1.0
        self._b: float = 0.0

    def fit(self, raw_probs: Sequence[float], labels: Sequence[int]) -> None:
        """Fit Platt scaling on held-out validation predictions.

        Args:
            raw_probs: Uncalibrated model output probabilities.
            labels: Ground-truth binary labels.
        """
        X = np.array(raw_probs).reshape(-1, 1)
        y = np.array(labels)
        lr = LogisticRegression(C=1e10, solver="lbfgs", max_iter=1000)
        lr.fit(X, y)
        self._lr = lr
        self._a = float(lr.coef_[0][0])
        self._b = float(lr.intercept_[0])
        logger.info("Platt calibration fit: a=%.4f b=%.4f", self._a, self._b)

    def calibrate(self, raw_prob: float) -> float:
        """Apply learned Platt scaling to a single probability."""
        if self._lr is None:
            return raw_prob
        return float(self._lr.predict_proba(np.array([[raw_prob]]))[0, 1])

    def calibrate_batch(self, raw_probs: Sequence[float]) -> np.ndarray:
        """Apply Platt scaling to an array of probabilities."""
        if self._lr is None:
            return np.array(raw_probs)
        X = np.array(raw_probs).reshape(-1, 1)
        return self._lr.predict_proba(X)[:, 1]

    @property
    def params(self) -> dict[str, float]:
        return {"a": self._a, "b": self._b}
