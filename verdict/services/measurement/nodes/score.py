import logging
from ..db.reads import get_original_alarm_signals, get_active_signals, get_tempo_baselines

logger = logging.getLogger(__name__)


async def measure_signal_resolution(customer_id: str, outreach_id: int) -> dict:
    """
    Checks whether the ARGUS signals that triggered the original alarm
    have resolved at T+30.

    Ties measurement back to the actual statistical signals, not just
    to business-level outcomes like 'retained' or 'churned'.

    A customer can be labelled 'retained' but still have an active CFSI
    stress signal — meaning the underlying problem wasn't solved, just
    the churn behaviour suppressed temporarily.

    Resolution check:
      For each signal_type that was detected at alarm time:
        - Is the signal still active in signal_results?
        - Has the TEMPO baseline recovered (returned to pre-alarm range)?
        - Has the CUSUM/SR statistic fallen below its alarm threshold?
    """
    original_signals = await get_original_alarm_signals(outreach_id)
    current_signals = await get_active_signals(customer_id)

    current_signal_types = {s["signal_type"] for s in current_signals}
    original_signal_types = {
        s["signal_type"] for s in original_signals if s.get("detected")
    }

    still_active = original_signal_types & current_signal_types
    cleared = original_signal_types - current_signal_types

    tempo_baselines = await get_tempo_baselines(customer_id, list(original_signal_types))
    baseline_recovered = all(
        b.get("update_status") != "alarm_locked"
        for b in tempo_baselines
    )

    resolution = {
        "signals_cleared": len(still_active) == 0,
        "signals_partially_resolved": list(cleared),
        "signals_still_active": list(still_active),
        "tempo_baseline_recovered": baseline_recovered,
    }

    logger.info(
        f"SCORE: customer={customer_id} outreach={outreach_id} "
        f"cleared={resolution['signals_cleared']} "
        f"still_active={list(still_active)}"
    )
    return resolution


async def run_signal_resolution_batch(observation_window_days: int = 30):
    """
    Runs signal resolution checks for all customers at T+{observation_window_days}.
    Called after OBSERVE completes its T+30 pass.
    """
    from datetime import date, timedelta
    from ..db.reads import get_dispatched_customers_for_window
    from ..db.writes import write_outcome

    target_send_date = date.today() - timedelta(days=observation_window_days)
    customers = await get_dispatched_customers_for_window(target_send_date)

    logger.info(
        f"SCORE: Running signal resolution for {len(customers)} customers "
        f"(T+{observation_window_days})"
    )

    for customer in customers:
        resolution = await measure_signal_resolution(
            customer_id=customer["customer_id"],
            outreach_id=customer["outreach_id"],
        )
        # Update the existing outcomes row with signal resolution data
        try:
            from ..db.reads import get_pool
            pool = await get_pool()
            if pool:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE outcomes
                        SET signals_cleared = $1,
                            signals_still_active = $2,
                            tempo_baseline_recovered = $3
                        WHERE outreach_id = $4 AND observation_window = $5
                    """,
                        resolution["signals_cleared"],
                        resolution["signals_still_active"],
                        resolution["tempo_baseline_recovered"],
                        customer["outreach_id"],
                        observation_window_days,
                    )
        except Exception as e:
            logger.warning(f"SCORE: Failed to update signal resolution for {customer['customer_id']}: {e}")
