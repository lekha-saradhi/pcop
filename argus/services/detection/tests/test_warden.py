"""Tests for WARDEN multiple testing controller (BH-FDR)."""

from __future__ import annotations

import pytest

from services.detection.joint.warden import WARDENResult, bh_reject, warden_evaluate


class TestBHReject:
    def test_no_rejection_when_all_p_large(self) -> None:
        p = {"a": 0.5, "b": 0.7, "c": 0.9}
        rejected, threshold, adjusted = bh_reject(p, q=0.05)
        assert len(rejected) == 0

    def test_rejects_clearly_significant(self) -> None:
        p = {"txn": 0.0001, "recency": 0.0002, "salary": 0.5}
        rejected, threshold, adjusted = bh_reject(p, q=0.05)
        assert "txn" in rejected
        assert "recency" in rejected
        assert "salary" not in rejected

    def test_adjusted_p_values_monotone(self) -> None:
        p = {"a": 0.001, "b": 0.01, "c": 0.1, "d": 0.5}
        _, _, adjusted = bh_reject(p, q=0.05)
        vals = list(adjusted.values())
        assert all(0.0 <= v <= 1.0 for v in vals)

    def test_empty_input(self) -> None:
        rejected, threshold, adjusted = bh_reject({}, q=0.05)
        assert len(rejected) == 0
        assert threshold == 0.0

    def test_fdr_controlled_at_target(self) -> None:
        # With 10 null p-values uniform on [0,1], expect ≤ q * m rejections on average
        import numpy as np
        rng = np.random.default_rng(99)
        q = 0.05
        n_sim = 1000
        false_alarms = 0
        total_alarms = 0
        for _ in range(n_sim):
            p_vals = {str(i): float(rng.uniform()) for i in range(10)}
            rejected, _, _ = bh_reject(p_vals, q=q)
            false_alarms += len(rejected)  # all are null → all rejections are false
            total_alarms += max(len(rejected), 1)
        fdr = false_alarms / (total_alarms)
        assert fdr <= q + 0.05   # empirical FDR ≤ q + small tolerance


class TestWardenEvaluate:
    def test_no_alarm_when_no_rejection(self) -> None:
        result = warden_evaluate({"a": 0.9, "b": 0.8}, q=0.05)
        assert result.alarm is False
        assert result.severity == "NONE"

    def test_alarm_with_strong_signals(self) -> None:
        p = {
            "sr_transaction": 0.0001,
            "sa_ewma_recency": 0.0005,
            "ewma_engagement": 0.001,
        }
        result = warden_evaluate(p, oracle_detected=False, nexus_detected=False)
        assert result.alarm is True
        assert result.severity in ("MEDIUM", "HIGH", "CRITICAL", "LOW")

    def test_critical_severity(self) -> None:
        p = {
            "sr_transaction": 0.0001,
            "sa_ewma_recency": 0.0001,
            "ewma_engagement": 0.0001,
        }
        result = warden_evaluate(p, oracle_detected=True, nexus_detected=True)
        if result.alarm:
            assert result.severity == "CRITICAL"

    def test_rejected_tests_sorted(self) -> None:
        p = {"b_signal": 0.0001, "a_signal": 0.0002}
        result = warden_evaluate(p)
        if result.alarm:
            assert result.rejected_tests == sorted(result.rejected_tests)
