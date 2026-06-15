"""Extract tabular features for HABITAT Pass 1 and Pass 2 scoring."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)

# Pass 1: 14 features derived from core banking data
PASS1_FEATURE_NAMES: list[str] = [
    "recency_days",           # days since last transaction
    "monetary_avg",           # avg transaction amount (last 90d)
    "monetary_total",         # total spend (last 90d)
    "frequency_30d",          # transaction count (last 30d)
    "frequency_90d",          # transaction count (last 90d)
    "decline_rate_30d",       # declined txn fraction (last 30d)
    "support_contacts_90d",   # support contact count (last 90d)
    "inactivity_streak_days", # consecutive days without any event
    "product_count",          # number of active products
    "digital_ratio",          # online+mobile txns / total txns
    "avg_utilization",        # credit utilisation ratio
    "complaint_open_count",   # unresolved complaints
    "tenure_days",            # days since account open
    "channel_diversity",      # distinct channels used (last 90d)
]

# Pass 2: 14 Pass 1 features + 9 life-event features = 23 total
PASS2_LIFE_EVENT_FEATURES: list[str] = [
    "life_event_income_change",    # boolean: income change detected (last 30d)
    "life_event_address_change",   # boolean: address change (last 60d)
    "life_event_employer_change",  # boolean: employer change (last 90d)
    "life_event_marriage",         # boolean: marriage-related update
    "life_event_new_child",        # boolean: dependant added
    "life_event_competitor_app",   # boolean: competitor app linked
    "life_event_large_withdrawal", # boolean: withdrawal > 3σ
    "life_event_fd_break",         # boolean: FD broken prematurely
    "life_event_count",            # total life events (last 90d)
]

PASS2_FEATURE_NAMES: list[str] = PASS1_FEATURE_NAMES + PASS2_LIFE_EVENT_FEATURES


def extract_pass1_features(
    customer_id: str,
    db_row: dict[str, Any],
    as_of_date: date,
) -> dict[str, float | int]:
    """Extract 14 Pass 1 tabular features from database row data.

    Args:
        customer_id: Customer identifier (for logging).
        db_row: Dict containing raw database fields. Expected keys match
                the column names from pcop.customers and pcop.transactions.
        as_of_date: Scoring reference date (prevents look-ahead bias).

    Returns:
        Dict mapping each PASS1_FEATURE_NAMES entry to a numeric value.

    Raises:
        KeyError: If a required field is missing from db_row.
    """
    tenure_days = (as_of_date - db_row["account_open_date"]).days

    recency_days = db_row.get("days_since_last_txn", 999)
    monetary_avg = db_row.get("avg_txn_amount_90d", 0.0)
    monetary_total = db_row.get("total_spend_90d", 0.0)
    frequency_30d = db_row.get("txn_count_30d", 0)
    frequency_90d = db_row.get("txn_count_90d", 0)

    total_attempts_30d = max(db_row.get("txn_attempts_30d", frequency_30d), 1)
    decline_rate_30d = db_row.get("declined_txn_count_30d", 0) / total_attempts_30d

    support_contacts_90d = db_row.get("support_contact_count_90d", 0)
    inactivity_streak_days = db_row.get("current_inactivity_streak_days", 0)
    product_count = db_row.get("active_product_count", 1)

    total_90d = max(frequency_90d, 1)
    digital_txn_90d = db_row.get("digital_txn_count_90d", 0)
    digital_ratio = digital_txn_90d / total_90d

    avg_utilization = min(db_row.get("avg_credit_utilization", 0.0), 1.0)
    complaint_open_count = db_row.get("open_complaint_count", 0)
    channel_diversity = db_row.get("distinct_channel_count_90d", 1)

    features = {
        "recency_days": float(recency_days),
        "monetary_avg": float(monetary_avg),
        "monetary_total": float(monetary_total),
        "frequency_30d": float(frequency_30d),
        "frequency_90d": float(frequency_90d),
        "decline_rate_30d": float(decline_rate_30d),
        "support_contacts_90d": float(support_contacts_90d),
        "inactivity_streak_days": float(inactivity_streak_days),
        "product_count": float(product_count),
        "digital_ratio": float(digital_ratio),
        "avg_utilization": float(avg_utilization),
        "complaint_open_count": float(complaint_open_count),
        "tenure_days": float(tenure_days),
        "channel_diversity": float(channel_diversity),
    }

    assert set(features.keys()) == set(PASS1_FEATURE_NAMES), (
        f"Feature set mismatch for customer {customer_id}"
    )
    logger.debug("customer_id=%s pass1_features extracted", customer_id)
    return features


def extract_pass2_features(
    customer_id: str,
    db_row: dict[str, Any],
    life_events: list[dict[str, Any]],
    as_of_date: date,
) -> dict[str, float | int]:
    """Extract 23 Pass 2 features (14 Pass 1 + 9 life event features).

    Args:
        customer_id: Customer identifier.
        db_row: Raw database fields (same schema as Pass 1).
        life_events: List of life event dicts from Layer 4 output.
                     Each dict has keys: event_type, event_date, confidence.
        as_of_date: Scoring reference date.

    Returns:
        Dict mapping all PASS2_FEATURE_NAMES entries to numeric values.
    """
    pass1 = extract_pass1_features(customer_id, db_row, as_of_date)

    event_types = {e["event_type"] for e in life_events if e.get("event_date") <= as_of_date}

    life_features: dict[str, float] = {
        "life_event_income_change": float("income_change" in event_types),
        "life_event_address_change": float("address_change" in event_types),
        "life_event_employer_change": float("employer_change" in event_types),
        "life_event_marriage": float("marriage" in event_types),
        "life_event_new_child": float("new_child" in event_types),
        "life_event_competitor_app": float("competitor_app" in event_types),
        "life_event_large_withdrawal": float("large_withdrawal" in event_types),
        "life_event_fd_break": float("fd_break" in event_types),
        "life_event_count": float(len(life_events)),
    }

    features = {**pass1, **life_features}
    assert set(features.keys()) == set(PASS2_FEATURE_NAMES), (
        f"Pass 2 feature set mismatch for customer {customer_id}"
    )
    return features
