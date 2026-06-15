"""Unit tests for tabular_features.py."""

from datetime import date

import pytest

from ml.features.tabular_features import (
    PASS1_FEATURE_NAMES,
    PASS2_FEATURE_NAMES,
    extract_pass1_features,
    extract_pass2_features,
)

_BASE_ROW: dict = {
    "account_open_date": date(2022, 1, 1),
    "days_since_last_txn": 5,
    "avg_txn_amount_90d": 1200.0,
    "total_spend_90d": 36000.0,
    "txn_count_30d": 8,
    "txn_count_90d": 22,
    "txn_attempts_30d": 10,
    "declined_txn_count_30d": 1,
    "support_contact_count_90d": 2,
    "current_inactivity_streak_days": 0,
    "active_product_count": 3,
    "digital_txn_count_90d": 18,
    "avg_credit_utilization": 0.45,
    "open_complaint_count": 0,
    "distinct_channel_count_90d": 2,
}


def test_pass1_returns_all_features() -> None:
    feats = extract_pass1_features("c1", _BASE_ROW, date(2024, 5, 1))
    assert set(feats.keys()) == set(PASS1_FEATURE_NAMES)


def test_pass1_feature_count() -> None:
    feats = extract_pass1_features("c1", _BASE_ROW, date(2024, 5, 1))
    assert len(feats) == 14


def test_decline_rate_clamped() -> None:
    row = {**_BASE_ROW, "declined_txn_count_30d": 0, "txn_attempts_30d": 0}
    feats = extract_pass1_features("c1", row, date(2024, 5, 1))
    assert 0.0 <= feats["decline_rate_30d"] <= 1.0


def test_utilization_clamped() -> None:
    row = {**_BASE_ROW, "avg_credit_utilization": 2.5}
    feats = extract_pass1_features("c1", row, date(2024, 5, 1))
    assert feats["avg_utilization"] <= 1.0


def test_tenure_days_computed() -> None:
    as_of = date(2024, 1, 1)
    feats = extract_pass1_features("c1", _BASE_ROW, as_of)
    assert feats["tenure_days"] == float((as_of - date(2022, 1, 1)).days)


def test_all_features_numeric() -> None:
    feats = extract_pass1_features("c1", _BASE_ROW, date(2024, 5, 1))
    for k, v in feats.items():
        assert isinstance(v, (int, float)), f"{k} is not numeric"


def test_pass2_returns_23_features() -> None:
    life_events = [{"event_type": "income_change", "event_date": date(2024, 4, 1), "confidence": 0.9}]
    feats = extract_pass2_features("c1", _BASE_ROW, life_events, date(2024, 5, 1))
    assert len(feats) == 23
    assert set(feats.keys()) == set(PASS2_FEATURE_NAMES)


def test_pass2_life_event_flags() -> None:
    life_events = [
        {"event_type": "income_change", "event_date": date(2024, 4, 1), "confidence": 0.9},
        {"event_type": "address_change", "event_date": date(2024, 3, 1), "confidence": 0.8},
    ]
    feats = extract_pass2_features("c1", _BASE_ROW, life_events, date(2024, 5, 1))
    assert feats["life_event_income_change"] == 1.0
    assert feats["life_event_address_change"] == 1.0
    assert feats["life_event_marriage"] == 0.0


def test_pass2_no_life_events() -> None:
    feats = extract_pass2_features("c1", _BASE_ROW, [], date(2024, 5, 1))
    assert feats["life_event_count"] == 0.0
