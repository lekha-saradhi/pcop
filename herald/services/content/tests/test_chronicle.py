import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ..nodes.chronicle import chronicle_node, _is_variant_b
from .conftest import make_state, make_brief

EMAIL_CONTENT = {
    "subject_line": "Hello Priya",
    "body_html": "<p>Your offer</p>",
    "cta_text": "See offer",
}


def _mock_db_writes(content_store_id=42):
    return patch.multiple(
        "services.content.nodes.chronicle",
        write_content_store=AsyncMock(return_value=content_store_id),
        update_outreach_log_status=AsyncMock(return_value=None),
        write_human_review_queue=AsyncMock(return_value=10),
    )


@pytest.mark.asyncio
async def test_chronicle_writes_content_store():
    state = make_state(
        generated_content=EMAIL_CONTENT,
        dispatched=True,
        compliance_status="passed",
    )

    mock_producer = MagicMock()
    mock_producer.produce = MagicMock()
    mock_producer.flush = MagicMock()

    with _mock_db_writes(content_store_id=42), \
         patch("services.content.nodes.chronicle.get_kafka_producer", return_value=mock_producer):
        result = await chronicle_node(state)

    assert result["content_store_id"] == 42


@pytest.mark.asyncio
async def test_chronicle_publishes_kafka_when_dispatched():
    state = make_state(
        generated_content=EMAIL_CONTENT,
        dispatched=True,
        compliance_status="passed",
    )

    mock_producer = MagicMock()
    mock_producer.produce = MagicMock()
    mock_producer.flush = MagicMock()

    with _mock_db_writes(), \
         patch("services.content.nodes.chronicle.get_kafka_producer", return_value=mock_producer):
        await chronicle_node(state)

    mock_producer.produce.assert_called_once()
    call_kwargs = mock_producer.produce.call_args
    assert call_kwargs.kwargs["topic"] == "pcop.dispatched.v1"
    assert call_kwargs.kwargs["key"] == "C-00000001"


@pytest.mark.asyncio
async def test_chronicle_no_kafka_when_not_dispatched():
    state = make_state(
        generated_content=EMAIL_CONTENT,
        dispatched=False,
        compliance_status="passed",
    )

    mock_producer = MagicMock()

    with _mock_db_writes(), \
         patch("services.content.nodes.chronicle.get_kafka_producer", return_value=mock_producer):
        await chronicle_node(state)

    mock_producer.produce.assert_not_called()


@pytest.mark.asyncio
async def test_chronicle_writes_human_review_queue_when_failed():
    state = make_state(
        generated_content=EMAIL_CONTENT,
        dispatched=False,
        human_review_required=True,
        compliance_status="human_review",
        compliance_notes="Regex: Prohibited phrase",
    )

    mock_producer = MagicMock()

    with _mock_db_writes(), \
         patch("services.content.nodes.chronicle.get_kafka_producer", return_value=mock_producer):
        await chronicle_node(state)

    from services.content.nodes.chronicle import write_human_review_queue
    write_human_review_queue.assert_called_once()


def test_is_variant_b_odd_customer():
    assert _is_variant_b("C-00000001") is True
    assert _is_variant_b("C-00000003") is True


def test_is_variant_b_even_customer():
    assert _is_variant_b("C-00000002") is False
    assert _is_variant_b("C-00000004") is False
