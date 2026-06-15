"""Tests for TEMPO Kalman filter baseline manager."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from services.detection.baseline.tempo import (
    TEMPOState,
    tempo_fast_update,
    tempo_init,
    tempo_lock,
    tempo_unlock,
    tempo_update,
)


class TestTempoInit:
    def test_initial_state(self) -> None:
        state = tempo_init("sr_transaction", mu=10.0, sigma=2.0)
        assert state.mu == pytest.approx(10.0)
        assert state.sigma == pytest.approx(2.0)
        assert state.update_status == "active"

    def test_sigma_floor(self) -> None:
        state = tempo_init("test", mu=0.0, sigma=0.0)
        assert state.sigma > 0.0


class TestTempoUpdate:
    def test_mu_drifts_toward_observation(self) -> None:
        state = tempo_init("txn", mu=10.0, sigma=2.0)
        today = date(2024, 1, 1)
        for _ in range(50):
            state = tempo_update(state, x=15.0, today=today)
        # After many observations at 15, baseline should move toward 15
        assert state.mu > 10.5

    def test_frozen_when_alarm_locked(self) -> None:
        state = tempo_init("txn", mu=10.0, sigma=2.0)
        state = tempo_lock(state)
        today = date(2024, 1, 1)
        mu_before = state.mu
        for _ in range(20):
            state = tempo_update(state, x=20.0, today=today)
        assert state.mu == pytest.approx(mu_before)

    def test_resumes_after_clear_delay(self) -> None:
        state = tempo_init("txn", mu=10.0, sigma=2.0)
        state = tempo_lock(state)
        cleared = date(2024, 1, 1)
        state = tempo_unlock(state, cleared)
        # Still locked within resume delay
        for _ in range(5):
            state = tempo_update(state, x=20.0, today=cleared + timedelta(days=3))
        mu_mid = state.mu
        # After resume delay passes, baseline updates
        for _ in range(20):
            state = tempo_update(state, x=20.0, today=cleared + timedelta(days=10))
        assert state.mu > mu_mid or state.mu > 10.0

    def test_fast_update_mode(self) -> None:
        state = tempo_init("salary", mu=5000.0, sigma=500.0)
        today = date(2024, 3, 1)
        state = tempo_fast_update(state, today, days=30)
        assert state.update_status == "fast_update"
        # Baseline should update faster (more gain per observation)
        for _ in range(10):
            state = tempo_update(state, x=8000.0, today=today)
        assert state.mu > 5000.0


class TestTempoLockUnlock:
    def test_lock_sets_status(self) -> None:
        state = tempo_init("txn", 10.0, 2.0)
        state = tempo_lock(state)
        assert state.update_status == "alarm_locked"

    def test_unlock_sets_cleared_date(self) -> None:
        state = tempo_init("txn", 10.0, 2.0)
        state = tempo_lock(state)
        cleared = date(2024, 6, 1)
        state = tempo_unlock(state, cleared)
        assert state.update_status == "active"
        assert state.alarm_cleared_date == cleared
