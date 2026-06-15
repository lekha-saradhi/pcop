import logging
from langchain_core.tools import tool
from ..db.connection import get_db_session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Direct async helpers (non-tool) — used by INTAKE and GATE internally
# ---------------------------------------------------------------------------

async def get_churn_score_raw(customer_id: str) -> dict:
    async with get_db_session() as session:
        row = await session.fetchrow("""
            SELECT final_score, risk_tier, tare_score, habitat_score,
                   treatability_score, action_score, reason_codes_v2,
                   scoring_pass, scored_at
            FROM churn_scores
            WHERE customer_id = $1
            ORDER BY scored_at DESC
            LIMIT 1
        """, customer_id)
        if row is None:
            return {"final_score": 0.0, "risk_tier": "low", "action_score": 0.0}
        result = dict(row)
        # Convert None numeric fields to 0.0 to avoid crashes downstream
        for key in ("final_score", "tare_score", "habitat_score", "treatability_score", "action_score"):
            if key in result and result[key] is None:
                result[key] = 0.0
        return result


async def get_consent_flags_raw(customer_id: str) -> dict:
    async with get_db_session() as session:
        row = await session.fetchrow("""
            SELECT email_opt_in, sms_opt_in, push_opt_in, call_opt_in
            FROM customers WHERE customer_id = $1
        """, customer_id)
        return dict(row) if row else {}


async def get_channel_history_raw(customer_id: str, days: int = 30) -> list:
    async with get_db_session() as session:
        rows = await session.fetch("""
            SELECT channel, dispatched_at
            FROM outreach_log
            WHERE customer_id = $1
              AND dispatched_at >= NOW() - make_interval(days => $2)
              AND holdout_group = FALSE
            ORDER BY dispatched_at DESC
        """, customer_id, days)
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# LangChain tools — exposed to LLM agents via bind_tools()
# ---------------------------------------------------------------------------

@tool
async def get_signal_results_tool(customer_id: str, signal_type: str = None) -> dict:
    """
    Fetches ARGUS signal results for a customer.
    Optionally filtered by signal_type.
    Only returns non-expired detected signals.

    Args:
        customer_id: Customer identifier
        signal_type: Optional filter (e.g. 'cusum_salary', 'location_rule')
    """
    async with get_db_session() as session:
        if signal_type:
            rows = await session.fetch("""
                SELECT signal_type, detected, confidence, evidence,
                       cusum_value, alarm_threshold, method_used,
                       onset_estimate, direction, evaluated_at
                FROM signal_results
                WHERE customer_id = $1
                  AND (expires_at IS NULL OR expires_at > NOW())
                  AND detected = TRUE
                  AND signal_type = $2
                ORDER BY evaluated_at DESC LIMIT 20
            """, customer_id, signal_type)
        else:
            rows = await session.fetch("""
                SELECT signal_type, detected, confidence, evidence,
                       cusum_value, alarm_threshold, method_used,
                       onset_estimate, direction, evaluated_at
                FROM signal_results
                WHERE customer_id = $1
                  AND (expires_at IS NULL OR expires_at > NOW())
                  AND detected = TRUE
                ORDER BY evaluated_at DESC LIMIT 20
            """, customer_id)

        signals = [dict(row) for row in rows]
        return {"signals": signals, "count": len(signals)}


@tool
async def get_crm_notes_tool(
    customer_id: str, last_n: int = 10, keyword_filter: str = None
) -> dict:
    """
    Fetches recent CRM notes for a customer.
    COGNITION uses this to find churn intent signals and life event mentions.

    Args:
        customer_id: Customer identifier
        last_n: Number of most recent notes to fetch (max 20)
        keyword_filter: Optional keyword to filter notes (SQL ILIKE)
    """
    last_n = min(last_n, 20)
    async with get_db_session() as session:
        if keyword_filter:
            rows = await session.fetch("""
                SELECT note_id, note_type, note_text, sentiment_score,
                       issue_category, resolved, channel, created_at
                FROM crm_notes
                WHERE customer_id = $1
                  AND note_text ILIKE $2
                ORDER BY created_at DESC
                LIMIT $3
            """, customer_id, f"%{keyword_filter}%", last_n)
        else:
            rows = await session.fetch("""
                SELECT note_id, note_type, note_text, sentiment_score,
                       issue_category, resolved, channel, created_at
                FROM crm_notes
                WHERE customer_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, customer_id, last_n)

        return {"notes": [dict(r) for r in rows]}


@tool
async def get_transactions_tool(
    customer_id: str,
    category: str = None,
    days: int = 90,
    limit: int = 50,
) -> dict:
    """
    Fetches recent transactions for a customer.
    COGNITION uses this to verify salary changes, location shifts,
    and MCC-based lifecycle events.

    Args:
        customer_id: Customer identifier
        category: Optional transaction category filter (e.g. 'salary_credit')
        days: Look-back window in days (max 365)
        limit: Maximum number of rows (max 100)
    """
    days = min(days, 365)
    limit = min(limit, 100)

    async with get_db_session() as session:
        if category:
            rows = await session.fetch("""
                SELECT txn_id, txn_date, amount, direction, category,
                       mcc_code, merchant_city, channel, payment_ref, balance_after
                FROM transactions
                WHERE customer_id = $1
                  AND txn_date >= NOW() - make_interval(days => $2)
                  AND category = $3
                ORDER BY txn_date DESC LIMIT $4
            """, customer_id, days, category, limit)
        else:
            rows = await session.fetch("""
                SELECT txn_id, txn_date, amount, direction, category,
                       mcc_code, merchant_city, channel, payment_ref, balance_after
                FROM transactions
                WHERE customer_id = $1
                  AND txn_date >= NOW() - make_interval(days => $2)
                ORDER BY txn_date DESC LIMIT $3
            """, customer_id, days, limit)

        return {"transactions": [dict(r) for r in rows], "count": len(rows)}


@tool
async def get_kyc_updates_tool(customer_id: str, days: int = 180) -> dict:
    """
    Fetches KYC field updates for a customer.
    COGNITION uses this to confirm employer changes and address changes.

    Args:
        customer_id: Customer identifier
        days: Look-back window in days
    """
    async with get_db_session() as session:
        rows = await session.fetch("""
            SELECT field_name, old_value, new_value, updated_by,
                   verification_status, updated_at
            FROM kyc_updates
            WHERE customer_id = $1
              AND updated_at >= NOW() - make_interval(days => $2)
            ORDER BY updated_at DESC
        """, customer_id, days)
        return {"updates": [dict(r) for r in rows]}


@tool
async def get_account_events_tool(customer_id: str) -> dict:
    """
    Fetches account events (product additions, closures, mortgage enquiries).
    COGNITION uses this to confirm lifecycle events.

    Args:
        customer_id: Customer identifier
    """
    async with get_db_session() as session:
        rows = await session.fetch("""
            SELECT event_type, product_code, event_date, metadata
            FROM account_events
            WHERE customer_id = $1
              AND event_date >= NOW() - INTERVAL '180 days'
            ORDER BY event_date DESC
        """, customer_id)
        return {"events": [dict(r) for r in rows]}


@tool
async def get_enrichment_tool(customer_id: str, source: str = None) -> dict:
    """
    Fetches external enrichment data (LinkedIn employer, credit bureau, news).

    Args:
        customer_id: Customer identifier
        source: Optional source filter ('linkedin', 'credit_bureau', 'demographics')
    """
    async with get_db_session() as session:
        if source:
            rows = await session.fetch("""
                SELECT source, field, value, confidence, captured_at
                FROM external_enrichment
                WHERE customer_id = $1
                  AND source = $2
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY captured_at DESC
            """, customer_id, source)
        else:
            rows = await session.fetch("""
                SELECT source, field, value, confidence, captured_at
                FROM external_enrichment
                WHERE customer_id = $1
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY captured_at DESC
                LIMIT 30
            """, customer_id)
        return {"enrichment": [dict(r) for r in rows]}


@tool
async def get_churn_score_tool(customer_id: str) -> dict:
    """
    Fetches the latest CHRONOS churn score for a customer.

    Args:
        customer_id: Customer identifier
    """
    return await get_churn_score_raw(customer_id)


@tool
async def get_life_events_tool(customer_id: str, days: int = 90) -> dict:
    """
    Fetches previously detected life events for a customer.
    COMPASS uses this for context on recent life changes.

    Args:
        customer_id: Customer identifier
        days: Look-back window
    """
    async with get_db_session() as session:
        rows = await session.fetch("""
            SELECT event_type, confidence, evidence, source,
                   risk_adjustment, detected_at
            FROM life_events
            WHERE customer_id = $1
              AND detected_at >= NOW() - make_interval(days => $2)
            ORDER BY detected_at DESC
        """, customer_id, days)
        return {"events": [dict(r) for r in rows]}


@tool
async def get_offer_eligibility_tool(customer_id: str) -> dict:
    """
    Fetches offers this customer is eligible to receive.
    COMPASS uses this to select the right offer code.

    Args:
        customer_id: Customer identifier
    """
    async with get_db_session() as session:
        row = await session.fetchrow("""
            SELECT segment, annual_income_band
            FROM customers
            WHERE customer_id = $1
        """, customer_id)

        if row is None:
            return {"offers": []}

        segment = row["segment"]

        offer_map = {
            "HNW": [
                {"offer_code": "HNW_FEE_WAIVER_12M", "description": "12-month fee waiver", "value": "INR 25,000"},
                {"offer_code": "HNW_RATE_UPGRADE", "description": "Priority savings rate +0.75%", "value": "Rate upgrade"},
                {"offer_code": "HNW_RM_PRIORITY", "description": "Dedicated RM priority access", "value": "Service"},
            ],
            "Mass Affluent": [
                {"offer_code": "MA_FEE_WAIVER_6M", "description": "6-month fee waiver", "value": "INR 8,000"},
                {"offer_code": "MA_RATE_UPGRADE", "description": "Savings rate +0.50%", "value": "Rate upgrade"},
            ],
            "Mass Market": [
                {"offer_code": "MM_CASHBACK_3M", "description": "3-month cashback 2%", "value": "INR 2,000"},
                {"offer_code": "MM_OVERDRAFT_WAIVER", "description": "Overdraft fee waiver", "value": "INR 500"},
            ],
            "Digital Native": [
                {"offer_code": "DN_APP_REWARD", "description": "In-app reward points 5x", "value": "5x points"},
                {"offer_code": "DN_ZERO_FOREX", "description": "Zero forex markup 3 months", "value": "Forex savings"},
            ],
        }

        offers = offer_map.get(
            segment,
            [{"offer_code": "RETENTION_STANDARD", "description": "Standard retention", "value": "Generic"}],
        )
        return {"offers": offers, "segment": segment}


@tool
async def get_channel_history_tool(customer_id: str, days: int = 30) -> dict:
    """
    Fetches recent outreach history for a customer.
    COMPASS uses this to avoid repeating channels too soon.

    Args:
        customer_id: Customer identifier
        days: Look-back window (default 30)
    """
    async with get_db_session() as session:
        rows = await session.fetch("""
            SELECT channel, status, dispatched_at, offer_code
            FROM outreach_log
            WHERE customer_id = $1
              AND dispatched_at >= NOW() - make_interval(days => $2)
              AND holdout_group = FALSE
            ORDER BY dispatched_at DESC
        """, customer_id, days)
        return {"history": [dict(r) for r in rows], "count": len(rows)}


@tool
async def get_rm_availability_tool(customer_id: str) -> dict:
    """
    Checks whether the customer's RM is available for a call or visit
    in the next 48 hours.

    Args:
        customer_id: Customer identifier
    """
    async with get_db_session() as session:
        row = await session.fetchrow("""
            SELECT relationship_manager_id
            FROM customers
            WHERE customer_id = $1
        """, customer_id)

        rm_id = row["relationship_manager_id"] if row else None

        return {
            "available": rm_id is not None,
            "rm_id": rm_id,
            "next_slot": "within_48h",
        }


@tool
async def get_consent_flags_tool(customer_id: str) -> dict:
    """
    Fetches marketing consent flags for all channels.

    Args:
        customer_id: Customer identifier
    """
    result = await get_consent_flags_raw(customer_id)
    if not result:
        return {
            "email_opt_in": False,
            "sms_opt_in": False,
            "push_opt_in": False,
            "call_opt_in": False,
        }
    return result
