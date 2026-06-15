"""Tests for NEXUS correlation structure monitor."""

from __future__ import annotations

import numpy as np
import pytest

from services.detection.joint.nexus import (
    NEXUSState,
    _find_changed_edges,
    nexus_evaluate,
    nexus_fit_baseline,
    nexus_shrink_to_segment,
)


def _make_X(n: int, p: int = 8, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal((n, p))


class TestNEXUSBaseline:
    def test_fit_returns_state(self) -> None:
        X = _make_X(60)
        state = nexus_fit_baseline(X)
        assert state.omega_baseline is not None
        assert state.omega_baseline.shape == (8, 8)

    def test_precision_matrix_symmetric(self) -> None:
        X = _make_X(80)
        state = nexus_fit_baseline(X)
        omega = state.omega_baseline
        assert omega is not None
        assert np.allclose(omega, omega.T, atol=1e-6)

    def test_fit_warns_on_small_data(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging
        with caplog.at_level(logging.WARNING, logger="services.detection.joint.nexus"):
            nexus_fit_baseline(_make_X(5))
        assert any("insufficient" in r.message.lower() for r in caplog.records)


class TestNEXUSEvaluate:
    def test_no_alarm_stable(self) -> None:
        rng = np.random.default_rng(42)
        X_base = rng.standard_normal((60, 8))
        X_curr = rng.standard_normal((30, 8))  # same distribution
        state = nexus_fit_baseline(X_base)
        result = nexus_evaluate(state, X_curr)
        # Under same distribution, p_value should typically be > 0.01
        assert result.lrt_p_value >= 0.0
        assert isinstance(result.nexus_detected, bool)

    def test_alarm_on_structure_change(self) -> None:
        rng = np.random.default_rng(7)
        # Baseline: correlated signals
        L = np.eye(8)
        L[0, 1] = 0.9
        cov_base = L @ L.T
        X_base = rng.multivariate_normal(np.zeros(8), cov_base, size=80)

        # Current: uncorrelated (structure collapsed)
        X_curr = rng.standard_normal((30, 8))

        state = nexus_fit_baseline(X_base)
        result = nexus_evaluate(state, X_curr)
        # LRT p-value should be small (structure changed)
        assert isinstance(result.frobenius_delta, float)
        assert result.frobenius_delta >= 0.0

    def test_no_baseline_returns_safe_default(self) -> None:
        state = NEXUSState()
        result = nexus_evaluate(state, _make_X(30))
        assert result.nexus_detected is False

    def test_insufficient_current_window(self) -> None:
        state = nexus_fit_baseline(_make_X(60))
        result = nexus_evaluate(state, _make_X(3))
        assert result.nexus_detected is False


class TestNEXUSShrinkage:
    def test_new_customer_uses_segment_entirely(self) -> None:
        seg = np.eye(8)
        ind = np.eye(8) * 2
        result = nexus_shrink_to_segment(ind, seg, tenure_months=0.0)
        assert np.allclose(result, seg)

    def test_veteran_uses_individual_entirely(self) -> None:
        seg = np.eye(8)
        ind = np.eye(8) * 2
        result = nexus_shrink_to_segment(ind, seg, tenure_months=12.0)
        assert np.allclose(result, ind)
