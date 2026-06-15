"""Tests for ORACLE multiscale changepoint detector."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest

from services.detection.joint.oracle import _lrt_per_dim, oracle_evaluate


def _dates(n: int, start: date = date(2024, 1, 1)) -> list[date]:
    return [start + timedelta(days=i) for i in range(n)]


def _make_X(n: int, p: int = 8, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).standard_normal((n, p))


class TestLRTPerDim:
    def test_zero_on_mean_observations(self) -> None:
        mus = np.zeros(8)
        sigmas = np.ones(8)
        X = np.zeros((14, 8))
        lrt = _lrt_per_dim(X, mus, sigmas)
        assert np.allclose(lrt, 0.0)

    def test_positive_on_mean_shift(self) -> None:
        mus = np.zeros(8)
        sigmas = np.ones(8)
        X = np.ones((14, 8)) * 5.0   # all dimensions shifted up by 5σ
        lrt = _lrt_per_dim(X, mus, sigmas)
        assert (lrt > 0).all()


class TestOracleEvaluate:
    def test_returns_no_alarm_stable(self) -> None:
        rng = np.random.default_rng(42)
        X = rng.standard_normal((60, 8))
        result = oracle_evaluate(X, _dates(60))
        assert isinstance(result.oracle_detected, bool)
        assert 0.0 <= result.p_value <= 1.0

    def test_alarm_on_large_mean_shift(self) -> None:
        rng = np.random.default_rng(1)
        X = np.vstack([
            rng.standard_normal((40, 8)),
            rng.standard_normal((20, 8)) + 10.0,  # massive shift in last 20 days
        ])
        dates = _dates(60)
        mus = np.zeros(8)
        sigmas = np.ones(8)
        result = oracle_evaluate(X, dates, mus=mus, sigmas=sigmas)
        assert result.oracle_detected is True
        assert result.alarm_scale in (7, 14, 30)
        assert result.onset_estimate is not None

    def test_insufficient_history(self) -> None:
        result = oracle_evaluate(_make_X(3), _dates(3))
        assert result.oracle_detected is False
        assert "insufficient" in result.evidence[0].lower()

    def test_dim_names_in_output(self) -> None:
        rng = np.random.default_rng(5)
        X = np.vstack([rng.standard_normal((40, 8)), rng.standard_normal((20, 8)) + 8.0])
        result = oracle_evaluate(X, _dates(60), mus=np.zeros(8), sigmas=np.ones(8))
        if result.oracle_detected:
            assert len(result.alarm_dimensions) > 0
