"""Extract cold-start features for customers with < 90 days tenure or < 30 events."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)

# 7 features available from day 1 (no historical transaction data required)
COLD_START_FEATURE_NAMES: list[str] = [
    "tenure_days",          # days since account open
    "product_count",        # number of active products at signup
    "age_bucket",           # encoded age band (0=<25, 1=25-34, 2=35-44, 3=45-54, 4=55+)
    "income_band",          # encoded income band (0-4)
    "channel_acquisition",  # acquisition channel (0=branch, 1=online, 2=referral, 3=agent)
    "credit_score_band",    # encoded credit score quintile (0-4)
    "city_tier",            # city tier (1=metro, 2=tier1, 3=tier2, 4=rural)
]

_AGE_BAND_MAP = {
    range(0, 25): 0,
    range(25, 35): 1,
    range(35, 45): 2,
    range(45, 55): 3,
    range(55, 120): 4,
}

_CHANNEL_MAP = {"branch": 0, "online": 1, "referral": 2, "agent": 3}


def _encode_age(age: int) -> int:
    for rng, band in _AGE_BAND_MAP.items():
        if age in rng:
            return band
    return 4


def extract_cold_start_features(
    customer_id: str,
    db_row: dict[str, Any],
    as_of_date: date,
) -> dict[str, float]:
    """Extract 7 cold-start features for a new or data-sparse customer.

    Args:
        customer_id: Customer identifier (for logging).
        db_row: Dict with onboarding data. Required keys:
                account_open_date, active_product_count, age,
                income_band, acquisition_channel, credit_score_band, city_tier.
        as_of_date: Scoring reference date.

    Returns:
        Dict mapping each COLD_START_FEATURE_NAMES entry to a float value.
    """
    tenure_days = float((as_of_date - db_row["account_open_date"]).days)
    product_count = float(db_row.get("active_product_count", 1))
    age_bucket = float(_encode_age(int(db_row.get("age", 35))))
    income_band = float(min(int(db_row.get("income_band", 2)), 4))
    channel_acquisition = float(_CHANNEL_MAP.get(db_row.get("acquisition_channel", "branch"), 0))
    credit_score_band = float(min(int(db_row.get("credit_score_band", 2)), 4))
    city_tier = float(min(max(int(db_row.get("city_tier", 1)), 1), 4))

    features = {
        "tenure_days": tenure_days,
        "product_count": product_count,
        "age_bucket": age_bucket,
        "income_band": income_band,
        "channel_acquisition": channel_acquisition,
        "credit_score_band": credit_score_band,
        "city_tier": city_tier,
    }

    assert set(features.keys()) == set(COLD_START_FEATURE_NAMES), (
        f"Cold-start feature set mismatch for customer {customer_id}"
    )
    logger.debug("customer_id=%s cold_start_features extracted", customer_id)
    return features
