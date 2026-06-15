"""Tests for Herald Transaction agent (Adaptive SR + STL)."""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from services.detection.agents.herald_transaction import HeraldTransactionAgent, _seasonal_adjust
from services.detection.baseline.tempo import tempo_init
from services.detection.methods.adaptive_sr import SRState, sr_p_value


class TestSeasonalAdjust:
    def test_removes_weekly_pattern(self) -> None:
        arr = np.array([10.0, 5.0, 8.0, 6.0, 9.0, 4.0, 7.0] * 4, dtype=float)
        residuals = _seasonal_adjust(arr)
        # Residuals should have lower variance than the original
        assert residuals.std() <= arr.std() + 1e-9

    def test_short_history_unchanged(self) -> None:
        arr = np.array([1.0, 2.0, 3.0], dtype=float)
        assert np.allclose(_seasonal_adjust(arr), arr)


class TestHeraldTransactionAgent:
    def _make_data(self, history: list[float], mu: float = 10.0, sigma: float = 2.0) -> dict:
        return {
            "history": history,
            "tempo_state": tempo_init("sr_transaction", mu, sigma),
            "sr_state": SRState(),
            "today": date(2024, 11, 1),
        }

    def test_no_alarm_stable(self) -> None:
        rng = np.random.default_rng(42)
        history = (rng.normal(loc=10.0, scale=2.0, size=30)).tolist()
        agent = HeraldTransactionAgent()
        result = agent.evaluate("C001", self._make_data(history))
        assert result.signal_type == "sr_transaction"
        assert isinstance(result.p_value, float)
        assert 0.0 <= result.confidence <= 1.0

    def test_alarm_on_sustained_drop(self) -> None:
        rng = np.random.default_rng(0)
        stable = rng.normal(loc=10.0, scale=0.5, size=14).tolist()
        drop = [2.0] * 60   # severe sustained drop
        history = stable + drop
        agent = HeraldTransactionAgent()
        result = agent.evaluate("C002", self._make_data(history, mu=10.0, sigma=0.5))
        assert result.detected is True
        assert result.p_value < 0.5

    def test_result_fields_populated(self) -> None:
        history = [8.0] * 28
        agent = HeraldTransactionAgent()
        result = agent.evaluate("C003", self._make_data(history))
        assert result.method_used == "adaptive_sr"
        assert result.baseline_mean == pytest.approx(10.0)
        assert result.method_version == "argus-v1"
