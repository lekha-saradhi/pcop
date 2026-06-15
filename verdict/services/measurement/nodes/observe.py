import logging
from datetime import date, timedelta
from ..db.reads import (
    get_dispatched_customers_for_window,
    get_transaction_volume,
    get_engagement_score,
    get_current_churn_score,
    get_active_signals,
    get_product_closures,
    get_balance_change,
    get_tempo_baselines,
)
from ..db.writes import write_outcome

logger = logging.getLogger(__name__)


async def observe_outcomes(observation_window_days: int):
    """
    Measures behavioural outcomes for all customers whose outreach
    occurred exactly {observation_window_days} days ago.

    Runs on schedule: T+1 daily 02:00, T+7 daily 02:30, T+30 daily 03:00

    Ties outcome measurement directly back to ARGUS signals:
      - Transaction volume change → measured against TEMPO baseline
      - Engagement score change → EWMA engagement vs pre-alarm TEMPO baseline
      - Signal resolution → did the ARGUS alarm clear?
      - CHRONOS rescore → did the churn score decrease?
      - Product closure → any account.status changed to 'closed'
    """
    target_send_date = date.today() - timedelta(days=observation_window_days)
    customers = await get_dispatched_customers_for_window(target_send_date)

    logger.info(
        f"OBSERVE: Measuring T+{observation_window_days} outcomes "
        f"for {len(customers)} customers dispatched on {target_send_date}"
    )

    for customer in customers:
        customer_id = customer["customer_id"]
        outreach_id = customer["outreach_id"]
        send_date = customer["dispatched_at"].date() if hasattr(customer["dispatched_at"], "date") else target_send_date

        outcome = await _measure_single_customer(
            customer_id=customer_id,
            send_date=send_date,
            observation_window=observation_window_days,
            pre_alarm_baseline=customer.get("argus_baseline"),
        )

        await write_outcome({
            "customer_id": customer_id,
            "outreach_id": outreach_id,
            "holdout_group": customer.get("holdout_group", False),
            "observation_window": observation_window_days,
            **outcome,
        })

        logger.info(
            f"OBSERVE: customer={customer_id} window={observation_window_days}d "
            f"label={outcome['outcome_label']} score_delta={outcome['score_reduction']:.3f}"
        )


async def _measure_single_customer(
    customer_id: str,
    send_date: date,
    observation_window: int,
    pre_alarm_baseline: dict,
) -> dict:
    """
    Measures all outcome dimensions for one customer.

    Key design decision: we compare post-outreach behaviour against
    ARGUS's pre-alarm TEMPO baseline (stored in tempo_baselines table),
    NOT against the post-alarm state. This is the correct counterfactual.

    If we compared against the alarmed state, natural recovery would look
    like outreach success. By using the pre-alarm baseline, we measure
    whether the customer returned to their normal behaviour.
    """
    observation_start = send_date
    observation_end = send_date + timedelta(days=observation_window)

    pre_alarm_baseline = pre_alarm_baseline or {}

    txn_volume = await get_transaction_volume(customer_id, observation_start, observation_end)
    engagement = await get_engagement_score(customer_id, observation_end)
    churn_score = await get_current_churn_score(customer_id)
    active_signals = await get_active_signals(customer_id)
    closures = await get_product_closures(customer_id, observation_start, observation_end)
    balance_change = await get_balance_change(customer_id, observation_start, observation_end)

    baseline_txn = pre_alarm_baseline.get("transaction_frequency_mu", 0)
    txn_recovery_pct = (
        (txn_volume - baseline_txn) / baseline_txn * 100
        if baseline_txn > 0 else 0
    )

    signals_cleared = len(active_signals) == 0

    score_at_send = pre_alarm_baseline.get("churn_score_at_send", 0.5)
    score_reduction = score_at_send - churn_score.get("final_score", score_at_send)

    outcome_label = _derive_outcome_label(
        churn_score=churn_score.get("final_score", 0.5),
        score_reduction=score_reduction,
        products_closed=len(closures),
        signals_cleared=signals_cleared,
    )

    return {
        "outcome_label": outcome_label,
        "txn_volume_change": txn_recovery_pct,
        "engagement_change": engagement.get("delta_vs_baseline", 0),
        "balance_change": balance_change,
        "products_closed": len(closures),
        "churn_score_at_measure": churn_score.get("final_score"),
        "score_reduction": score_reduction,
        "signals_cleared": signals_cleared,
        "active_signal_count": len(active_signals),
        "measured_at": date.today().isoformat(),
    }


def _derive_outcome_label(
    churn_score: float,
    score_reduction: float,
    products_closed: int,
    signals_cleared: bool,
) -> str:
    """
    Derives a human-interpretable outcome label.
    Uses CHRONOS risk tiers for consistency.
    """
    if products_closed > 0:
        return "churned"
    if churn_score < 0.40 and score_reduction > 0.10:
        return "retained"
    if churn_score < 0.65 and score_reduction > 0.05:
        return "partial"
    if score_reduction < 0.02 and not signals_cleared:
        return "unresponsive"
    return "partial"
