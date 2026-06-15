"""Load customer data from the PCOP Bank Demo API and build CustomerRecord objects."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

import requests

from services.scoring.serving.batch_scorer import CustomerRecord

logger = logging.getLogger(__name__)

BANK_API_BASE = "http://localhost:3001/api"

# All tokens remapped to the 8 types TARE was fine-tuned on
_TRANSACTION_TOKEN_MAP: dict[str, str] = {
    "salary_credit": "ONLINE_PURCHASE",
    "fee": "CARD_SWIPE",
    "retail": "CARD_SWIPE",
    "atm": "CARD_TAP",
    "transfer": "ONLINE_TRANSFER",
    "debit": "CARD_SWIPE",
}

_ACCOUNT_EVENT_TOKEN_MAP: dict[str, str] = {
    "PRODUCT_ADD": "BILL_PAYMENT",
    "MORTGAGE_ENQUIRY": "BILL_PAYMENT",
    "ACCOUNT_CLOSURE_REQUEST": "COMPLAINT_RAISED",
    "WILL_SERVICE_ENQUIRY": "BILL_PAYMENT",
    "LIFE_INSURANCE_OPEN": "BILL_PAYMENT",
    "JOINT_ACCOUNT_OPEN": "BILL_PAYMENT",
}

_APP_EVENT_TOKEN_MAP: dict[str, str] = {
    "login": "SUPPORT_CONTACT",
    "feature_view": "ONLINE_TRANSFER",
    "transfer": "ONLINE_TRANSFER",
}

_CRM_NOTE_TOKEN_MAP: dict[str, str] = {
    "complaint": "COMPLAINT_RAISED",
    "support": "SUPPORT_CONTACT",
}

_INCOME_BAND_MAP: dict[str, int] = {
    "below_5L": 0,
    "5L_10L": 1,
    "10L_25L": 2,
    "above_25L": 3,
}

_CITY_TIER_MAP: dict[str, int] = {
    "Mumbai": 1, "Delhi": 1, "Bangalore": 1, "Chennai": 1,
    "Hyderabad": 1, "Kolkata": 1,
    "Pune": 2, "Ahmedabad": 2, "Jaipur": 2,
}

_CREDIT_SCORE_BAND_MAP: dict[str, int] = {
    "poor": 0, "fair": 1, "good": 2, "very_good": 3, "excellent": 4,
}


def _get_json(url: str, params: dict | None = None) -> dict:
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _fetch_customers() -> list[dict]:
    data = _get_json(f"{BANK_API_BASE}/core-banking/customers", {"limit": 200})
    return data["data"]


def _fetch_customer_full(customer_id: str) -> dict:
    return _get_json(f"{BANK_API_BASE}/core-banking/customers/{customer_id}")["data"]


def _fetch_transactions(customer_id: str) -> list[dict]:
    data = _get_json(f"{BANK_API_BASE}/core-banking/transactions", {"customer_id": customer_id, "limit": 1000})
    return data["data"]


def _fetch_transaction_summary(customer_id: str) -> dict:
    data = _get_json(f"{BANK_API_BASE}/core-banking/transactions/summary", {"customer_id": customer_id})
    return data["data"]


def _fetch_account_events(customer_id: str) -> list[dict]:
    data = _get_json(f"{BANK_API_BASE}/core-banking/account-events", {"customer_id": customer_id})
    return data["data"]


def _fetch_crm_notes(customer_id: str) -> list[dict]:
    data = _get_json(f"{BANK_API_BASE}/crm/notes", {"customer_id": customer_id, "limit": 100})
    return data["data"]


def _fetch_app_events(customer_id: str) -> list[dict]:
    data = _get_json(f"{BANK_API_BASE}/app-events", {"customer_id": customer_id, "limit": 500})
    return data["data"]


def _fetch_kyc_updates(customer_id: str) -> list[dict]:
    data = _get_json(f"{BANK_API_BASE}/core-banking/kyc-updates", {"customer_id": customer_id})
    return data["data"]


def _build_token_sequence(
    customer: dict,
    transactions: list[dict],
    account_events: list[dict],
    app_events: list[dict],
    crm_notes: list[dict],
    as_of_date: date,
) -> tuple[list[int], list[float]]:
    """Transform bank data into token IDs and time gaps for TARE."""
    from ml.features.sequence_builder import build_sequence

    actions: list[tuple[str, date]] = []

    for txn in transactions:
        txn_date = datetime.fromisoformat(txn["txn_date"]).date()
        if txn_date > as_of_date:
            continue
        token_name = _TRANSACTION_TOKEN_MAP.get(txn.get("category", ""))
        if token_name:
            actions.append((token_name, txn_date))

    for evt in account_events:
        evt_date = datetime.fromisoformat(evt["event_date"]).date() if isinstance(evt["event_date"], str) else date.fromisoformat(evt["event_date"])
        if evt_date > as_of_date:
            continue
        token_name = _ACCOUNT_EVENT_TOKEN_MAP.get(evt.get("event_type", ""))
        if token_name:
            actions.append((token_name, evt_date))

    for evt in app_events:
        evt_ts = evt.get("event_timestamp", "")
        if not evt_ts:
            continue
        evt_date = datetime.fromisoformat(evt_ts.replace("Z", "+00:00")).date()
        if evt_date > as_of_date:
            continue
        token_name = _APP_EVENT_TOKEN_MAP.get(evt.get("event_type", ""))
        if token_name:
            actions.append((token_name, evt_date))

    for note in crm_notes:
        note_date = datetime.fromisoformat(note["created_at"].replace("Z", "+00:00")).date()
        if note_date > as_of_date:
            continue
        token_name = _CRM_NOTE_TOKEN_MAP.get(note.get("note_type", ""))
        if token_name:
            actions.append((token_name, note_date))

    actions.sort(key=lambda x: x[1])

    if not actions:
        from ml.features.sequence_builder import MAX_SEQ_LEN, PAD_ID
        return [PAD_ID] * MAX_SEQ_LEN, [0.0] * MAX_SEQ_LEN

    action_names, action_dates = zip(*actions)
    token_ids, time_gaps = build_sequence(
        customer.get("customer_id", "unknown"),
        list(action_names),
        list(action_dates),
        as_of_date,
    )
    return token_ids, time_gaps


def _build_tabular_features(
    customer: dict,
    customer_full: dict,
    transactions: list[dict],
    txn_summary: dict,
    crm_notes: list[dict],
    account_events: list[dict],
    enrichment: dict,
    as_of_date: date,
) -> dict[str, float]:
    """Aggregate bank data into the 14 PASS1 tabular features."""
    tenure_days = int(customer.get("tenure_years", 0)) * 365

    recency_days = txn_summary.get("days_since_last_txn", 999)

    now = datetime.combine(as_of_date, datetime.min.time())
    cutoff_90d = (now - timedelta(days=90)).date()
    cutoff_30d = (now - timedelta(days=30)).date()

    txn_90d = [t for t in transactions if datetime.fromisoformat(t["txn_date"]).date() >= cutoff_90d]
    txn_30d = [t for t in transactions if datetime.fromisoformat(t["txn_date"]).date() >= cutoff_30d]

    amounts_90d = [float(t["amount"]) for t in txn_90d if t["direction"] == "debit"]
    monetary_avg = sum(amounts_90d) / len(amounts_90d) if amounts_90d else 0.0
    monetary_total = sum(amounts_90d)

    frequency_30d = len(txn_30d)
    frequency_90d = len(txn_90d)

    decline_count_30d = sum(1 for t in txn_30d if t.get("category") in ("decline",))
    total_attempt_30d = max(len(txn_30d), 1)
    decline_rate_30d = decline_count_30d / total_attempt_30d

    support_count_90d = sum(
        1 for n in crm_notes
        if n.get("note_type") in ("support", "complaint")
        and datetime.fromisoformat(n["created_at"].replace("Z", "+00:00")).date() >= cutoff_90d
    )

    inactivity_streak_days = recency_days

    accounts = customer_full.get("accounts", [])
    product_count = len(accounts)

    digital_channels = {"upi", "neft", "rtgs", "imps", "card", "wallet"}
    txn_channels = {t.get("channel", "") for t in txn_90d if t.get("channel")}
    digital_txn_count_90d = sum(1 for t in txn_90d if t.get("channel", "") in digital_channels)
    digital_ratio = digital_txn_count_90d / max(frequency_90d, 1)

    open_complaints = sum(1 for n in crm_notes if n.get("note_type") == "complaint" and not n.get("resolved", True))

    all_events = set()
    for t in txn_90d:
        if t.get("channel"):
            all_events.add(t["channel"])
    channel_diversity = len(all_events)

    income_to_amount = {"below_5L": 500000, "5L_10L": 1000000, "10L_25L": 2500000, "above_25L": 5000000}
    income_band = customer.get("annual_income_band", "5L_10L")
    annual_income = income_to_amount.get(income_band, 1000000)
    quarterly_income = annual_income / 4
    avg_credit_utilization = min(monetary_total / max(quarterly_income, 1), 1.0)

    db_row: dict[str, Any] = {
        "days_since_last_txn": recency_days,
        "avg_txn_amount_90d": monetary_avg,
        "total_spend_90d": monetary_total,
        "txn_count_30d": frequency_30d,
        "txn_count_90d": frequency_90d,
        "txn_attempts_30d": total_attempt_30d,
        "declined_txn_count_30d": decline_count_30d,
        "support_contact_count_90d": support_count_90d,
        "current_inactivity_streak_days": inactivity_streak_days,
        "active_product_count": product_count,
        "digital_txn_count_90d": digital_txn_count_90d,
        "avg_credit_utilization": avg_credit_utilization,
        "open_complaint_count": open_complaints,
        "tenure_days": tenure_days,
        "distinct_channel_count_90d": channel_diversity,
        "account_open_date": (now - timedelta(days=tenure_days)).date(),
    }

    from ml.features.tabular_features import extract_pass1_features
    return extract_pass1_features(customer.get("customer_id", "unknown"), db_row, as_of_date)


def load_customers_from_bank_api(
    api_base: str = "http://localhost:3001",
    as_of_date: date | None = None,
) -> list[CustomerRecord]:
    """Fetch all customers from the PCOP Bank Demo API and build CustomerRecord objects.

    Args:
        api_base: Base URL of the bank API server.
        as_of_date: Reference date for feature extraction (defaults to today).

    Returns:
        List of CustomerRecord objects ready for the CHRONOS scoring pipeline.
    """
    global BANK_API_BASE
    BANK_API_BASE = f"{api_base}/api"
    as_of_date = as_of_date or date.today()

    customers = _fetch_customers()
    logger.info("Fetched %d customers from bank API", len(customers))

    records: list[CustomerRecord] = []
    for cust in customers:
        cid = cust["customer_id"]
        try:
            customer_full = _fetch_customer_full(cid)
            transactions = _fetch_transactions(cid)
            txn_summary = _fetch_transaction_summary(cid)
            account_events = _fetch_account_events(cid)
            app_events = _fetch_app_events(cid)
            crm_notes = _fetch_crm_notes(cid)

            enrichment_raw = {}
            try:
                enrichment_raw = _get_json(f"{BANK_API_BASE}/enrichment/{cid}").get("data", {})
            except Exception:
                pass

            token_ids, time_gaps = _build_token_sequence(
                cust, transactions, account_events, app_events, crm_notes, as_of_date,
            )

            tabular_features = _build_tabular_features(
                cust, customer_full, transactions, txn_summary, crm_notes, account_events, enrichment_raw, as_of_date,
            )

            records.append(CustomerRecord(
                customer_id=cid,
                token_ids=token_ids,
                time_gaps=time_gaps,
                tabular_features=tabular_features,
                tenure_days=int(cust.get("tenure_years", 0)) * 365,
            ))
            logger.debug("Built CustomerRecord for %s (tenure=%dy, txns=%d, events=%d)",
                         cid, cust.get("tenure_years", 0), len(transactions), len(account_events))
        except Exception:
            logger.exception("Failed to load customer %s from bank API", cid)

    logger.info("Loaded %d / %d customer records from bank API", len(records), len(customers))
    return records
