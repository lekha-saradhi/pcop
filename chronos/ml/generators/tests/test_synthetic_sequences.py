"""Unit tests for synthetic sequence generator."""

import pytest
from pathlib import Path

from ml.features.sequence_builder import MAX_SEQ_LEN, PAD_ID


def _make_dummy_row(churner: bool = False) -> dict:
    return {
        "CLIENTNUM": "12345",
        "Total_Trans_Ct": 50,
        "Total_Ct_Chng_Q4_Q1": 1.2,
        "Months_Inactive_12_mon": 2,
        "Contacts_Count_12_mon": 1,
        "Avg_Utilization_Ratio": 0.4,
        "Attrition_Flag": "Attrited Customer" if churner else "Existing Customer",
    }


def test_sequence_length() -> None:
    from ml.generators.synthetic_sequences_from_bankchurners import _build_sequence_for_row
    import random

    rng = random.Random(42)
    row = _make_dummy_row()
    tokens = _build_sequence_for_row(row, rng)
    assert len(tokens) <= MAX_SEQ_LEN


def test_only_known_tokens() -> None:
    from ml.generators.synthetic_sequences_from_bankchurners import _build_sequence_for_row
    from ml.features.sequence_builder import VOCAB
    import random

    rng = random.Random(42)
    row = _make_dummy_row()
    tokens = _build_sequence_for_row(row, rng)

    known = set(VOCAB.keys())
    for token in tokens:
        assert token in known, f"Unknown token: {token}"


def test_churner_gets_complaint_token() -> None:
    from ml.generators.synthetic_sequences_from_bankchurners import _build_sequence_for_row
    import random

    rng = random.Random(42)
    row = {**_make_dummy_row(churner=True), "Contacts_Count_12_mon": 5}
    tokens = _build_sequence_for_row(row, rng)
    assert "COMPLAINT_RAISED" in tokens


def test_inactivity_token_inserted_for_inactive() -> None:
    from ml.generators.synthetic_sequences_from_bankchurners import _build_sequence_for_row
    import random

    rng = random.Random(42)
    row = {**_make_dummy_row(), "Months_Inactive_12_mon": 6}
    tokens = _build_sequence_for_row(row, rng)
    assert "INACTIVITY_14D" in tokens
