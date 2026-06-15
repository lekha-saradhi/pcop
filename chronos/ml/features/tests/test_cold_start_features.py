"""Unit tests for cold_start_features.py."""

from datetime import date

from ml.features.cold_start_features import (
    COLD_START_FEATURE_NAMES,
    extract_cold_start_features,
)

_BASE_ROW = {
    "account_open_date": date(2024, 3, 1),
    "active_product_count": 2,
    "age": 32,
    "income_band": 2,
    "acquisition_channel": "online",
    "credit_score_band": 3,
    "city_tier": 1,
}


def test_returns_all_features() -> None:
    feats = extract_cold_start_features("c1", _BASE_ROW, date(2024, 5, 1))
    assert set(feats.keys()) == set(COLD_START_FEATURE_NAMES)


def test_feature_count() -> None:
    feats = extract_cold_start_features("c1", _BASE_ROW, date(2024, 5, 1))
    assert len(feats) == 7


def test_tenure_days_computed() -> None:
    as_of = date(2024, 5, 1)
    feats = extract_cold_start_features("c1", _BASE_ROW, as_of)
    assert feats["tenure_days"] == float((as_of - date(2024, 3, 1)).days)


def test_age_bucket_encoding() -> None:
    row = {**_BASE_ROW, "age": 28}  # 25-34 → bucket 1
    feats = extract_cold_start_features("c1", row, date(2024, 5, 1))
    assert feats["age_bucket"] == 1.0

    row["age"] = 22  # <25 → bucket 0
    feats = extract_cold_start_features("c1", row, date(2024, 5, 1))
    assert feats["age_bucket"] == 0.0


def test_income_band_clamped() -> None:
    row = {**_BASE_ROW, "income_band": 99}
    feats = extract_cold_start_features("c1", row, date(2024, 5, 1))
    assert feats["income_band"] == 4.0


def test_city_tier_clamped() -> None:
    row = {**_BASE_ROW, "city_tier": 0}
    feats = extract_cold_start_features("c1", row, date(2024, 5, 1))
    assert feats["city_tier"] >= 1.0


def test_unknown_channel_defaults() -> None:
    row = {**_BASE_ROW, "acquisition_channel": "unknown_channel"}
    feats = extract_cold_start_features("c1", row, date(2024, 5, 1))
    assert feats["channel_acquisition"] == 0.0


def test_all_values_floats() -> None:
    feats = extract_cold_start_features("c1", _BASE_ROW, date(2024, 5, 1))
    for k, v in feats.items():
        assert isinstance(v, float), f"{k} is not float"
