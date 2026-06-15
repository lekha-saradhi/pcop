"""Tests for ECHO signal expiry and alarm payload building."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from services.detection.state.echo import (
    SIGNAL_TTL_DAYS,
    AlarmPayload,
    ECHOPublisher,
    build_alarm_payload,
    is_signal_expired,
    signal_expires_at,
)


class TestSignalTTL:
    def test_all_signal_types_have_ttl(self) -> None:
        expected = {
            "sr_transaction", "sa_ewma_recency", "cusum_salary",
            "beta_cusum_sentiment", "ewma_engagement", "cfsi_stress",
            "location_rule", "lifecycle_mcc", "nexus_correlation",
            "oracle_multivariate",
        }
        assert expected.issubset(SIGNAL_TTL_DAYS.keys())

    def test_expires_at_correct_offset(self) -> None:
        now = datetime(2024, 1, 1, tzinfo=timezone.utc)
        expiry = signal_expires_at("sr_transaction", now)
        assert expiry == now + timedelta(days=21)

    def test_location_ttl_is_90(self) -> None:
        assert SIGNAL_TTL_DAYS["location_rule"] == 90

    def test_not_expired_immediately(self) -> None:
        now = datetime.now(tz=timezone.utc) - timedelta(seconds=10)
        assert not is_signal_expired("oracle_multivariate", now)


class TestBuildAlarmPayload:
    def _build(self, severity: str = "HIGH") -> AlarmPayload:
        now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        return build_alarm_payload(
            customer_id="C_TEST",
            severity=severity,
            rejected_tests=["sr_transaction", "ewma_engagement"],
            adjusted_p={"sr_transaction": 0.001, "ewma_engagement": 0.003},
            signal_details={"sr_transaction": {"method": "adaptive_sr", "statistic": 120.0}},
            nexus_changed=False,
            oracle_onset=date(2024, 6, 1),
            active_signal_count=2,
            now=now,
        )

    def test_payload_fields(self) -> None:
        payload = self._build()
        assert payload.customer_id == "C_TEST"
        assert payload.alarm_severity == "HIGH"
        assert "sr_transaction" in payload.rejected_tests
        assert payload.oracle_onset_estimate == "2024-06-01"
        assert payload.active_signal_count == 2

    def test_expires_at_is_max_ttl(self) -> None:
        payload = self._build()
        # rejected tests: sr_transaction (21d), ewma_engagement (14d) → max=21d
        now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        expected = (now + timedelta(days=21)).isoformat()
        assert payload.expires_at == expected

    def test_null_oracle_onset(self) -> None:
        now = datetime(2024, 6, 15, tzinfo=timezone.utc)
        payload = build_alarm_payload(
            customer_id="C2",
            severity="LOW",
            rejected_tests=["cfsi_stress"],
            adjusted_p={},
            signal_details={},
            nexus_changed=False,
            oracle_onset=None,
            active_signal_count=1,
            now=now,
        )
        assert payload.oracle_onset_estimate is None


class TestECHOPublisher:
    def test_log_fallback_when_kafka_unavailable(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging
        publisher = ECHOPublisher(bootstrap_servers="invalid_host:9999")
        payload = AlarmPayload(
            customer_id="C001",
            alarm_timestamp="2024-01-01T00:00:00+00:00",
            alarm_severity="LOW",
            rejected_tests=["sr_transaction"],
            fdr_adjusted_p_values={"sr_transaction": 0.01},
            signal_details={},
            nexus_structure_changed=False,
            oracle_onset_estimate=None,
            active_signal_count=1,
            expires_at="2024-01-22T00:00:00+00:00",
        )
        with caplog.at_level(logging.INFO, logger="services.detection.state.echo"):
            publisher.publish(payload)
        assert any("alarm" in r.message.lower() or "C001" in r.message for r in caplog.records)
