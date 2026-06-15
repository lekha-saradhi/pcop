import json
import logging
from typing import Optional
from .connection import get_db_session

logger = logging.getLogger(__name__)

OFFER_CATALOG = {
    "HNW_FEE_WAIVER_12M": {
        "description": "Annual fee waiver for 12 months on your premium account",
        "value": "₹12,000 saved",
    },
    "HNW_RM_UPGRADE": {
        "description": "Dedicated relationship manager assignment",
        "value": "Priority access + exclusive rates",
    },
    "MA_RATE_UPGRADE": {
        "description": "Preferential savings rate upgrade",
        "value": "0.5% additional p.a. on savings balance",
    },
    "MA_CASHBACK_6M": {
        "description": "5% cashback on utility and grocery spends for 6 months",
        "value": "Up to ₹6,000",
    },
    "MM_CASHBACK_3M": {
        "description": "3% cashback on all spends for 3 months",
        "value": "Up to ₹3,000",
    },
    "MM_ZERO_FEE": {
        "description": "Zero maintenance fee for 6 months",
        "value": "₹3,000 saved",
    },
    "DN_PREMIUM_UPGRADE": {
        "description": "Premium digital banking plan upgrade",
        "value": "Free for 6 months (₹1,499/month thereafter)",
    },
    "BEREAVEMENT_SUPPORT": {
        "description": "Dedicated bereavement support — fee waivers and estate assistance",
        "value": "Waived fees + priority estate handling",
    },
    "STRESS_RELIEF_EMI": {
        "description": "EMI holiday — defer 2 loan payments interest-free",
        "value": "Up to ₹20,000 deferred",
    },
    "MARRIAGE_BUNDLE": {
        "description": "Wedding banking bundle — joint account + home loan pre-approval",
        "value": "Zero processing fee + preferential rate",
    },
    "HOME_LOAN_OFFER": {
        "description": "Pre-approved home loan with preferential rate",
        "value": "0.25% rate reduction + zero processing fee",
    },
    "BABY_SAVINGS_PLAN": {
        "description": "Child savings plan — high-yield account for baby",
        "value": "7.5% p.a. for first year",
    },
    "RETIREMENT_INCOME": {
        "description": "Senior citizen fixed deposit — guaranteed monthly income",
        "value": "8.25% p.a. + monthly payout",
    },
    "MONITOR": {
        "description": "Monitoring — no active offer",
        "value": "",
    },
}


async def get_customer_profile(customer_id: str) -> dict:
    try:
        async with get_db_session() as conn:
            row = await conn.fetchrow("""
                SELECT customer_id, full_name, segment, tenure_years,
                       preferred_channel, email, phone_mobile
                FROM customers
                WHERE customer_id = $1
            """, customer_id)
            if row:
                return dict(row)
    except Exception as e:
        logger.warning(f"DB read failed for customer profile {customer_id}: {e}")
    return {
        "customer_id": customer_id,
        "full_name": f"Demo Customer {customer_id[-4:]}",
        "segment": "Mass Affluent",
        "tenure_years": 3.5,
        "preferred_channel": "email",
        "email": f"demo_{customer_id.lower()}@example.com",
        "phone_mobile": "+910000000000",
    }


async def get_churn_score_with_reasons(customer_id: str) -> dict:
    try:
        async with get_db_session() as conn:
            row = await conn.fetchrow("""
                SELECT final_score, risk_tier, tare_score, habitat_score,
                       treatability_score, action_score, reason_codes_v2,
                       scoring_pass, scored_at
                FROM churn_scores
                WHERE customer_id = $1
                ORDER BY scored_at DESC
                LIMIT 1
            """, customer_id)
            if row:
                data = dict(row)
                if data.get("reason_codes_v2"):
                    rc = data["reason_codes_v2"]
                    data["reason_codes_v2"] = json.loads(rc) if isinstance(rc, str) else rc
                return data
    except Exception as e:
        logger.warning(f"DB read failed for churn score {customer_id}: {e}")
    return {
        "final_score": 0.75,
        "risk_tier": "high",
        "treatability_score": 0.6,
        "action_score": 0.45,
        "reason_codes_v2": [],
    }


async def get_signal_results(customer_id: str) -> list[dict]:
    try:
        async with get_db_session() as conn:
            rows = await conn.fetch("""
                SELECT signal_type, confidence, evidence, onset_estimate,
                       direction, method_used, detected
                FROM signal_results
                WHERE customer_id = $1
                  AND detected = TRUE
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY confidence DESC
            """, customer_id)
            result = []
            for r in rows:
                d = dict(r)
                if isinstance(d.get("evidence"), str):
                    d["evidence"] = json.loads(d["evidence"])
                result.append(d)
            return result
    except Exception as e:
        logger.warning(f"DB read failed for signal results {customer_id}: {e}")
    return []


async def get_offer_details(offer_code: Optional[str]) -> dict:
    if not offer_code:
        return {"description": "", "value": ""}
    return OFFER_CATALOG.get(offer_code, {"description": offer_code, "value": ""})


async def get_best_prompt_version(channel: str, segment: str, risk_tier: str) -> dict:
    try:
        async with get_db_session() as conn:
            row = await conn.fetchrow("""
                SELECT pv.version_id, pv.system_prompt, pv.few_shot_examples,
                       pv.tone_instructions, pv.offer_instructions,
                       pp.conversion_rate, pp.bandit_alpha, pp.bandit_beta
                FROM prompt_versions pv
                JOIN prompt_performance pp USING (version_id)
                WHERE pv.channel = $1
                  AND pv.segment = $2
                  AND pv.risk_tier = $3
                  AND pv.is_active = TRUE
                ORDER BY pp.bandit_alpha / (pp.bandit_alpha + pp.bandit_beta) DESC
                LIMIT 1
            """, channel, segment, risk_tier)
            if row:
                data = dict(row)
                if data.get("few_shot_examples"):
                    fe = data["few_shot_examples"]
                    data["few_shot_examples"] = json.loads(fe) if isinstance(fe, str) else fe
                return data
    except Exception as e:
        logger.warning(f"DB read failed for prompt version: {e}")
    return {
        "version_id": "default",
        "system_prompt": "",
        "few_shot_examples": [],
        "tone_instructions": "",
        "offer_instructions": "",
    }


async def get_prior_outreach(customer_id: str, limit: int = 2) -> list[dict]:
    try:
        async with get_db_session() as conn:
            rows = await conn.fetch("""
                SELECT ol.channel, ol.dispatched_at, cs.subject_line, cs.body_content
                FROM outreach_log ol
                JOIN content_store cs USING (outreach_id)
                WHERE ol.customer_id = $1
                  AND ol.status = 'sent'
                ORDER BY ol.dispatched_at DESC
                LIMIT $2
            """, customer_id, limit)
            return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"DB read failed for prior outreach {customer_id}: {e}")
    return []


async def get_account_summary(customer_id: str) -> dict:
    try:
        async with get_db_session() as conn:
            rows = await conn.fetch("""
                SELECT product_type, balance, account_tenure_years
                FROM accounts
                WHERE customer_id = $1
                  AND status = 'active'
            """, customer_id)
            return {"accounts": [dict(r) for r in rows]}
    except Exception as e:
        logger.warning(f"DB read failed for account summary {customer_id}: {e}")
    return {"accounts": []}


async def get_customer_contact(customer_id: str) -> dict:
    try:
        async with get_db_session() as conn:
            row = await conn.fetchrow("""
                SELECT email, phone_mobile
                FROM customers
                WHERE customer_id = $1
            """, customer_id)
            if row:
                return dict(row)
    except Exception as e:
        logger.warning(f"DB read failed for customer contact {customer_id}: {e}")
    return {
        "email": f"demo_{customer_id.lower()}@example.com",
        "phone_mobile": "+910000000000",
    }


async def get_push_token(customer_id: str) -> str:
    try:
        async with get_db_session() as conn:
            row = await conn.fetchrow("""
                SELECT push_token
                FROM device_tokens
                WHERE customer_id = $1
                  AND is_active = TRUE
                ORDER BY updated_at DESC
                LIMIT 1
            """, customer_id)
            if row:
                return row["push_token"] or ""
    except Exception as e:
        logger.warning(f"DB read failed for push token {customer_id}: {e}")
    return ""
