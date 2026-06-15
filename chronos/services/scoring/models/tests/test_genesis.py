"""Unit tests for GENESIS cold-start scorer."""

import pytest

from services.scoring.models.genesis_scorer import (
    GENESISScorer,
    GRADUATION_TENURE_DAYS,
    GRADUATION_MIN_TOKENS,
)


def test_graduation_threshold() -> None:
    scorer = GENESISScorer()
    assert scorer.is_graduated(GRADUATION_TENURE_DAYS, GRADUATION_MIN_TOKENS) is True
    assert scorer.is_graduated(GRADUATION_TENURE_DAYS - 1, GRADUATION_MIN_TOKENS) is False
    assert scorer.is_graduated(GRADUATION_TENURE_DAYS, GRADUATION_MIN_TOKENS - 1) is False


def test_graduation_above_threshold() -> None:
    scorer = GENESISScorer()
    assert scorer.is_graduated(200, 50) is True


def test_load_raises_when_missing() -> None:
    scorer = GENESISScorer(model_path="/nonexistent/path/model.pkl")
    with pytest.raises(FileNotFoundError):
        scorer.load()
