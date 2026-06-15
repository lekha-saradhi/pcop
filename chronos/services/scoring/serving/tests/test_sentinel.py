"""Unit tests for SENTINEL real-time scorer trigger logic."""

import pytest

from services.scoring.serving.sentinel_realtime import _should_trigger, TRIGGER_EVENTS


def test_triggers_on_closure_event() -> None:
    event = {"event_type": "ACCOUNT_CLOSURE_REQUEST"}
    assert _should_trigger(event, current_score=0.1, is_high_tier=False) is True


def test_triggers_on_bocpd() -> None:
    event = {"event_type": "SOME_EVENT", "bocpd_fired": True}
    assert _should_trigger(event, current_score=0.1, is_high_tier=False) is True


def test_triggers_on_high_score_crossing() -> None:
    event = {"event_type": "CARD_SWIPE"}
    assert _should_trigger(event, current_score=0.82, is_high_tier=False) is True


def test_triggers_on_high_tier() -> None:
    event = {"event_type": "CARD_SWIPE"}
    assert _should_trigger(event, current_score=0.20, is_high_tier=True) is True


def test_no_trigger_low_risk_low_tier() -> None:
    event = {"event_type": "CARD_SWIPE"}
    assert _should_trigger(event, current_score=0.10, is_high_tier=False) is False


def test_no_trigger_medium_score_not_high_tier() -> None:
    event = {"event_type": "MOBILE_LOGIN"}
    assert _should_trigger(event, current_score=0.50, is_high_tier=False) is False


def test_all_trigger_event_types() -> None:
    for event_type in TRIGGER_EVENTS:
        event = {"event_type": event_type}
        assert _should_trigger(event, current_score=0.0, is_high_tier=False) is True
