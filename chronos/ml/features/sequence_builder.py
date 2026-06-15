"""Build token sequences from customer action histories for TARE input."""

from __future__ import annotations

import logging
from datetime import date
from typing import Final

import numpy as np

logger = logging.getLogger(__name__)

# Token vocabulary — 50 action types
VOCAB: Final[dict[str, int]] = {
    "PAD": 0,
    "UNK": 1,
    "CARD_SWIPE": 2,
    "CARD_TAP": 3,
    "ATM_WITHDRAW": 4,
    "ATM_DEPOSIT": 5,
    "ONLINE_PURCHASE": 6,
    "ONLINE_TRANSFER": 7,
    "BILL_PAYMENT": 8,
    "STANDING_ORDER": 9,
    "DIRECT_DEBIT": 10,
    "SALARY_CREDIT": 11,
    "INTEREST_CREDIT": 12,
    "FEE_DEBIT": 13,
    "DECLINE_INSUFFICIENT": 14,
    "DECLINE_FRAUD": 15,
    "DECLINE_OTHER": 16,
    "SUPPORT_CONTACT": 17,
    "COMPLAINT_RAISED": 18,
    "COMPLAINT_RESOLVED": 19,
    "MOBILE_LOGIN": 20,
    "WEB_LOGIN": 21,
    "BRANCH_VISIT": 22,
    "PRODUCT_ENQUIRY": 23,
    "LOAN_APPLICATION": 24,
    "LOAN_DISBURSED": 25,
    "LOAN_REPAYMENT": 26,
    "LOAN_OVERDUE": 27,
    "CARD_ACTIVATION": 28,
    "CARD_BLOCK": 29,
    "CARD_REPLACE": 30,
    "LIMIT_INCREASE_REQ": 31,
    "LIMIT_DECREASE": 32,
    "STATEMENT_VIEW": 33,
    "NOTIFICATION_OPEN": 34,
    "OFFER_CLICK": 35,
    "OFFER_REDEEM": 36,
    "SAVINGS_DEPOSIT": 37,
    "SAVINGS_WITHDRAW": 38,
    "FD_OPEN": 39,
    "FD_CLOSE": 40,
    "FOREX_BUY": 41,
    "FOREX_SELL": 42,
    "INACTIVITY_7D": 43,
    "INACTIVITY_14D": 44,
    "INACTIVITY_30D": 45,
    "ACCOUNT_CLOSURE_REQUEST": 46,
    "PROFILE_UPDATE": 47,
    "ADDRESS_CHANGE": 48,
    "NOMINEE_UPDATE": 49,
}

VOCAB_SIZE: Final[int] = len(VOCAB)
MAX_SEQ_LEN: Final[int] = 180
MIN_SEQ_LEN: Final[int] = 30  # below → cold-start route

PAD_ID: Final[int] = VOCAB["PAD"]
UNK_ID: Final[int] = VOCAB["UNK"]

_INACTIVITY_TOKENS = {7: "INACTIVITY_7D", 14: "INACTIVITY_14D", 30: "INACTIVITY_30D"}


def _encode_token(action: str) -> int:
    return VOCAB.get(action, UNK_ID)


def _insert_inactivity_tokens(
    actions: list[str], timestamps: list[date]
) -> tuple[list[str], list[date]]:
    """Insert INACTIVITY tokens wherever gaps exceed 7, 14, or 30 days."""
    if len(actions) < 2:
        return actions, timestamps

    enriched_actions: list[str] = [actions[0]]
    enriched_ts: list[date] = [timestamps[0]]

    for i in range(1, len(actions)):
        gap_days = (timestamps[i] - timestamps[i - 1]).days
        for threshold in sorted(_INACTIVITY_TOKENS, reverse=True):
            if gap_days >= threshold:
                enriched_actions.append(_INACTIVITY_TOKENS[threshold])
                enriched_ts.append(timestamps[i - 1])
                break
        enriched_actions.append(actions[i])
        enriched_ts.append(timestamps[i])

    return enriched_actions, enriched_ts


def build_sequence(
    customer_id: str,
    actions: list[str],
    timestamps: list[date],
    as_of_date: date,
) -> tuple[list[int], list[float]]:
    """Convert a customer's action history to token IDs and time gaps.

    Args:
        customer_id: Identifier (used for logging only).
        actions: Ordered list of action type strings.
        timestamps: Corresponding event dates (same length as actions).
        as_of_date: Scoring reference date; events after this are excluded.

    Returns:
        Tuple of (token_ids, time_gaps) each of length ≤ MAX_SEQ_LEN,
        left-padded with PAD to MAX_SEQ_LEN.
        time_gaps[i] = days since previous event (0 for first token).

    Raises:
        ValueError: If actions and timestamps differ in length.
    """
    if len(actions) != len(timestamps):
        raise ValueError(
            f"actions length {len(actions)} != timestamps length {len(timestamps)}"
        )

    # Filter future events
    pairs = [(a, t) for a, t in zip(actions, timestamps) if t <= as_of_date]
    if not pairs:
        logger.debug("customer_id=%s: no events before as_of_date=%s", customer_id, as_of_date)
        return [PAD_ID] * MAX_SEQ_LEN, [0.0] * MAX_SEQ_LEN

    acts, ts = zip(*pairs)
    acts_list = list(acts)
    ts_list = list(ts)

    acts_enriched, ts_enriched = _insert_inactivity_tokens(acts_list, ts_list)

    # Truncate to last MAX_SEQ_LEN events
    acts_enriched = acts_enriched[-MAX_SEQ_LEN:]
    ts_enriched = ts_enriched[-MAX_SEQ_LEN:]

    token_ids = [_encode_token(a) for a in acts_enriched]
    time_gaps = [0.0] + [
        float((ts_enriched[i] - ts_enriched[i - 1]).days)
        for i in range(1, len(ts_enriched))
    ]

    # Left-pad to MAX_SEQ_LEN
    pad_len = MAX_SEQ_LEN - len(token_ids)
    token_ids = [PAD_ID] * pad_len + token_ids
    time_gaps = [0.0] * pad_len + time_gaps

    return token_ids, time_gaps


def is_cold_start(token_ids: list[int]) -> bool:
    """Return True if the sequence has fewer than MIN_SEQ_LEN non-PAD tokens."""
    non_pad = sum(1 for t in token_ids if t != PAD_ID)
    return non_pad < MIN_SEQ_LEN


def sequence_to_array(token_ids: list[int], time_gaps: list[float]) -> tuple[np.ndarray, np.ndarray]:
    """Convert lists to numpy arrays suitable for model input."""
    return np.array(token_ids, dtype=np.int64), np.array(time_gaps, dtype=np.float32)
