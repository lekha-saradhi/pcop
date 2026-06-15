"""Unit tests for HABITAT Pass 2 scorer."""

import pytest

from services.scoring.models.habitat_pass2 import (
    is_eligible_for_pass2,
    merge_life_event_features,
    PASS2_TRIGGER_SCORE,
    PASS2_MIN_LIFE_EVENTS,
)

_PASS1_FEATURES = {
    "recency_days": 5.0,
    "monetary_avg": 1200.0,
    "monetary_total": 36000.0,
    "frequency_30d": 8.0,
    "frequency_90d": 22.0,
    "decline_rate_30d": 0.05,
    "support_contacts_90d": 2.0,
    "inactivity_streak_days": 0.0,
    "product_count": 3.0,
    "digital_ratio": 0.7,
    "avg_utilization": 0.4,
    "complaint_open_count": 0.0,
    "tenure_days": 365.0,
    "channel_diversity": 2.0,
}


def test_eligible_when_score_and_events_sufficient() -> None:
    assert is_eligible_for_pass2(PASS2_TRIGGER_SCORE, PASS2_MIN_LIFE_EVENTS) is True


def test_not_eligible_below_score_threshold() -> None:
    assert is_eligible_for_pass2(PASS2_TRIGGER_SCORE - 0.01, 3) is False


def test_not_eligible_zero_life_events() -> None:
    assert is_eligible_for_pass2(0.80, 0) is False


def test_merge_adds_9_features() -> None:
    events = [{"event_type": "income_change"}, {"event_type": "address_change"}]
    merged = merge_life_event_features(_PASS1_FEATURES, events)
    assert len(merged) == 23


def test_merge_flags_correct_events() -> None:
    events = [{"event_type": "income_change"}]
    merged = merge_life_event_features(_PASS1_FEATURES, events)
    assert merged["life_event_income_change"] == 1.0
    assert merged["life_event_marriage"] == 0.0


def test_merge_event_count() -> None:
    events = [{"event_type": "income_change"}, {"event_type": "address_change"}, {"event_type": "marriage"}]
    merged = merge_life_event_features(_PASS1_FEATURES, events)
    assert merged["life_event_count"] == 3.0


def test_merge_empty_events() -> None:
    merged = merge_life_event_features(_PASS1_FEATURES, [])
    assert merged["life_event_count"] == 0.0
    assert merged["life_event_income_change"] == 0.0
