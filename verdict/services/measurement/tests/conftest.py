import pytest
from datetime import date, datetime, timezone


def make_customer(
    customer_id="C-00000001",
    churn_score=0.72,
    treatability=0.6,
    holdout=False,
):
    return {
        "customer_id": customer_id,
        "outreach_id": int(customer_id.replace("C-", "")),
        "dispatched_at": datetime(2024, 11, 1, tzinfo=timezone.utc),
        "holdout_group": holdout,
        "treatability_score": treatability,
        "final_score": churn_score,
        "argus_baseline": {
            "transaction_frequency_mu": 15.0,
            "churn_score_at_send": churn_score,
        },
    }


def make_interaction_event(
    event_type="clicked",
    customer_id="C-00000001",
    channel="email",
    outreach_id=1,
):
    return {
        "event_id": "evt-001",
        "outreach_id": outreach_id,
        "customer_id": customer_id,
        "channel": channel,
        "event_type": event_type,
        "event_timestamp": datetime(2024, 11, 2, 10, 0, tzinfo=timezone.utc).isoformat(),
        "duration_seconds": None,
        "outcome": None,
        "link_url": None,
        "variant": None,
    }


def make_holdout_entry(
    customer_id="C-00000001",
    campaign_id="camp-2024-11",
    days_ago=5,
    score=0.75,
):
    from datetime import timedelta
    return {
        "customer_id": customer_id,
        "campaign_id": campaign_id,
        "risk_tier_at_entry": "high",
        "entered_holdout_at": datetime.now(timezone.utc) - timedelta(days=days_ago),
    }
