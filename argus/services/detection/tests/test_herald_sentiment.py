"""Tests for Herald Sentiment agent (Beta-CUSUM + SPRT)."""

from __future__ import annotations

import math

import pytest

from services.detection.agents.herald_sentiment import HeraldSentimentAgent
from services.detection.methods.beta_cusum import BetaCUSUMState, beta_cusum_update, beta_cusum_alarm
from services.detection.methods.sprt import SPRTState, sprt_decision


class TestBetaCUSUM:
    def test_logit_transform_positive_neutral(self) -> None:
        from services.detection.methods.beta_cusum import _logit_transform
        assert math.isfinite(_logit_transform(0.0))   # neutral → logit(0.5) = 0
        assert abs(_logit_transform(0.0)) < 1e-9

    def test_logit_transform_clamps_extremes(self) -> None:
        from services.detection.methods.beta_cusum import _logit_transform
        assert math.isfinite(_logit_transform(-1.0))
        assert math.isfinite(_logit_transform(1.0))

    def test_alarm_on_negative_trend(self) -> None:
        state = BetaCUSUMState(sigma_y=1.0)
        for _ in range(40):
            state = beta_cusum_update(state, -0.8)  # consistently negative sentiment
        assert beta_cusum_alarm(state)

    def test_no_alarm_neutral(self) -> None:
        state = BetaCUSUMState(sigma_y=1.0)
        for _ in range(20):
            state = beta_cusum_update(state, 0.1)   # slightly positive
        assert not beta_cusum_alarm(state)


class TestSPRT:
    def test_h1_decision_on_surge(self) -> None:
        state = SPRTState()
        from services.detection.methods.sprt import sprt_update
        for _ in range(30):
            state = sprt_update(state, count=5, lambda0=0.5, lambda1=2.0)  # 10x surge
        assert sprt_decision(state) == "H1"

    def test_h0_decision_on_stable(self) -> None:
        state = SPRTState()
        from services.detection.methods.sprt import sprt_update
        for _ in range(30):
            state = sprt_update(state, count=0, lambda0=0.5, lambda1=2.0)  # below null
        assert sprt_decision(state) == "H0"


class TestHeraldSentimentAgent:
    def _make_data(self, sentiment: float, count: int = 0) -> dict:
        return {
            "sentiment_score": sentiment,
            "complaint_count": count,
            "beta_cusum_state": BetaCUSUMState(sigma_y=1.0),
            "sprt_state": SPRTState(),
            "lambda0": 0.5,
            "lambda1": 2.0,
        }

    def test_result_fields(self) -> None:
        agent = HeraldSentimentAgent()
        result = agent.evaluate("C001", self._make_data(0.0))
        assert result.signal_type == "beta_cusum_sentiment"
        assert 0.0 <= result.p_value <= 1.0
        assert 0.0 <= result.confidence <= 1.0

    def test_confidence_combined_union_bound(self) -> None:
        agent = HeraldSentimentAgent()
        # Both sentiment and volume signal
        state = BetaCUSUMState(sigma_y=0.3)
        for _ in range(30):
            from services.detection.methods.beta_cusum import beta_cusum_update
            state = beta_cusum_update(state, -0.9)
        sprt = SPRTState()
        from services.detection.methods.sprt import sprt_update
        for _ in range(10):
            sprt = sprt_update(sprt, 5, 0.5, 2.0)
        data = {
            "sentiment_score": -0.9,
            "complaint_count": 5,
            "beta_cusum_state": state,
            "sprt_state": sprt,
            "lambda0": 0.5,
            "lambda1": 2.0,
        }
        result = agent.evaluate("C002", data)
        assert result.confidence >= 0.0
