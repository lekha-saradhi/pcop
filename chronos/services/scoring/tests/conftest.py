"""Pytest fixtures for CHRONOS integration tests."""

from __future__ import annotations

from datetime import date, datetime
from typing import Generator

import pytest

DUMMY_CUSTOMERS = [
    {
        "customer_id": f"DUMMY_{i:04d}",
        "tenure_days": 180 + i * 10,
        "token_ids": [0] * 150 + [2, 3, 6, 7, 11] * 6,
        "time_gaps": [0.0] * 150 + [1.0] * 30,
        "tabular_features": {
            "recency_days": float(5 + i % 10),
            "monetary_avg": 1200.0 + i * 50,
            "monetary_total": 36000.0,
            "frequency_30d": 8.0,
            "frequency_90d": 22.0,
            "decline_rate_30d": 0.05,
            "support_contacts_90d": float(i % 3),
            "inactivity_streak_days": 0.0,
            "product_count": 3.0,
            "digital_ratio": 0.7,
            "avg_utilization": 0.4 + (i % 5) * 0.05,
            "complaint_open_count": 0.0,
            "tenure_days": float(180 + i * 10),
            "channel_diversity": 2.0,
        },
        "label": int(i % 5 == 0),
    }
    for i in range(20)
]

COLD_START_CUSTOMER = {
    "customer_id": "COLD_001",
    "tenure_days": 30,
    "token_ids": [0] * 170 + [2, 3, 6, 7, 11] * 2,
    "time_gaps": [0.0] * 170 + [1.0] * 10,
    "tabular_features": {
        "tenure_days": 30.0,
        "product_count": 2.0,
        "age_bucket": 1.0,
        "income_band": 2.0,
        "channel_acquisition": 1.0,
        "credit_score_band": 3.0,
        "city_tier": 1.0,
    },
}


@pytest.fixture()
def dummy_customers() -> list[dict]:
    return DUMMY_CUSTOMERS


@pytest.fixture()
def cold_start_customer() -> dict:
    return COLD_START_CUSTOMER


@pytest.fixture()
def sample_tabular_features() -> dict:
    return DUMMY_CUSTOMERS[0]["tabular_features"]


@pytest.fixture()
def sample_token_ids() -> list[int]:
    return DUMMY_CUSTOMERS[0]["token_ids"]


@pytest.fixture()
def sample_time_gaps() -> list[float]:
    return DUMMY_CUSTOMERS[0]["time_gaps"]
