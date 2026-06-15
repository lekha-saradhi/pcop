"""Unit tests for sequence_builder.py."""

from datetime import date

import pytest

from ml.features.sequence_builder import (
    MAX_SEQ_LEN,
    MIN_SEQ_LEN,
    PAD_ID,
    VOCAB_SIZE,
    build_sequence,
    is_cold_start,
)


def _make_actions(n: int) -> tuple[list[str], list[date]]:
    actions = ["CARD_SWIPE"] * n
    timestamps = [date(2024, 1, i + 1) for i in range(n)]
    return actions, timestamps


def test_vocab_size() -> None:
    assert VOCAB_SIZE == 50


def test_output_length() -> None:
    actions, ts = _make_actions(50)
    token_ids, time_gaps = build_sequence("c1", actions, ts, date(2024, 12, 31))
    assert len(token_ids) == MAX_SEQ_LEN
    assert len(time_gaps) == MAX_SEQ_LEN


def test_left_padding() -> None:
    actions, ts = _make_actions(10)
    token_ids, _ = build_sequence("c1", actions, ts, date(2024, 12, 31))
    assert token_ids[0] == PAD_ID
    assert token_ids[MAX_SEQ_LEN - 10 - 1] == PAD_ID


def test_future_events_excluded() -> None:
    actions = ["CARD_SWIPE", "ONLINE_PURCHASE"]
    ts = [date(2024, 1, 1), date(2024, 6, 1)]
    as_of = date(2024, 3, 1)
    token_ids, _ = build_sequence("c1", actions, ts, as_of)
    non_pad = [t for t in token_ids if t != PAD_ID]
    assert len(non_pad) == 1


def test_mismatched_lengths_raises() -> None:
    with pytest.raises(ValueError):
        build_sequence("c1", ["CARD_SWIPE"], [], date(2024, 1, 1))


def test_truncation_to_max_len() -> None:
    actions, ts = _make_actions(MAX_SEQ_LEN + 50)
    token_ids, _ = build_sequence("c1", actions, ts, date(2024, 12, 31))
    assert len(token_ids) == MAX_SEQ_LEN


def test_is_cold_start_sparse() -> None:
    actions, ts = _make_actions(MIN_SEQ_LEN - 1)
    token_ids, _ = build_sequence("c1", actions, ts, date(2024, 12, 31))
    assert is_cold_start(token_ids) is True


def test_is_cold_start_sufficient() -> None:
    actions, ts = _make_actions(MIN_SEQ_LEN + 5)
    token_ids, _ = build_sequence("c1", actions, ts, date(2024, 12, 31))
    assert is_cold_start(token_ids) is False


def test_inactivity_token_inserted() -> None:
    from ml.features.sequence_builder import VOCAB

    actions = ["CARD_SWIPE", "CARD_SWIPE"]
    ts = [date(2024, 1, 1), date(2024, 2, 15)]  # 45-day gap → INACTIVITY_30D
    token_ids, _ = build_sequence("c1", actions, ts, date(2024, 12, 31))
    non_pad = [t for t in token_ids if t != PAD_ID]
    assert VOCAB["INACTIVITY_30D"] in non_pad


def test_time_gaps_non_negative() -> None:
    actions, ts = _make_actions(30)
    _, time_gaps = build_sequence("c1", actions, ts, date(2024, 12, 31))
    assert all(g >= 0 for g in time_gaps)
