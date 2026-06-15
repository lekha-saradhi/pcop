import json
import logging
from .connection import get_db_session

logger = logging.getLogger(__name__)


async def write_content_store(data: dict) -> int:
    try:
        async with get_db_session() as conn:
            row = await conn.fetchrow("""
                INSERT INTO content_store (
                    outreach_id, channel, subject_line, body_content,
                    ab_variant_content, cta_text, compliance_status,
                    compliance_notes, prompt_version, llm_model,
                    content_strategy, tone_modifiers, reason_codes_used
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING content_store_id
            """,
                data.get("outreach_id"),
                data.get("channel"),
                data.get("subject_line"),
                data.get("body_content"),
                data.get("ab_variant_content"),
                data.get("cta_text"),
                data.get("compliance_status"),
                data.get("compliance_notes"),
                data.get("prompt_version"),
                data.get("llm_model"),
                data.get("content_strategy"),
                data.get("tone_modifiers", []),
                json.dumps(data.get("reason_codes_used", [])),
            )
            return row["content_store_id"]
    except Exception as e:
        logger.error(f"Failed to write content_store: {e}")
        return -1


async def update_outreach_log_status(outreach_id: int, status: str) -> None:
    if outreach_id is None:
        return
    try:
        async with get_db_session() as conn:
            await conn.execute("""
                UPDATE outreach_log
                SET status = $1, updated_at = NOW()
                WHERE outreach_id = $2
            """, status, outreach_id)
    except Exception as e:
        logger.error(f"Failed to update outreach_log status for {outreach_id}: {e}")


async def write_human_review_queue(data: dict) -> int:
    try:
        async with get_db_session() as conn:
            row = await conn.fetchrow("""
                INSERT INTO human_review_queue (
                    outreach_id, customer_id, channel, content_store_id,
                    compliance_notes, priority, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING review_id
            """,
                data.get("outreach_id"),
                data.get("customer_id"),
                data.get("channel"),
                data.get("content_store_id"),
                data.get("compliance_notes"),
                data.get("priority", 3),
                data.get("created_at"),
            )
            return row["review_id"]
    except Exception as e:
        logger.error(f"Failed to write human_review_queue: {e}")
        return -1
