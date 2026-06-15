"""
APScheduler configuration for all ORACLE cycles.
Scheduled tasks per spec:

  HOLDOUT rescue check    → Hourly
  T+1 outcome measurement → Daily 02:00
  T+7 outcome measurement → Daily 02:30
  T+30 outcome measurement→ Daily 03:00
  DR uplift attribution   → Daily 04:00
  FUSION-X recalibration  → Daily 04:30
  Prompt bandit update    → Daily 05:00
  A/B significance test   → Daily 05:30
  Channel policy update   → Daily every hour (real-time-ish)
  LLM narration           → Nightly 06:00
  CHRONOS full retrain    → Weekly Sunday 02:00
  CAUSAL-NET retrain      → On calibration failure (pcop.model_signals.v1 consumer)

Usage:
    python -m services.analytics.scheduler
"""
import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

DEMO_MODE = os.environ.get("ORACLE_DEMO_MODE", "true").lower() == "true"


async def _observe_t1():
    from .cycles.retrain import run_weekly_retrain  # import guard — real import below
    # Import separately to avoid circular at module load
    import importlib
    observe_mod = importlib.import_module("services.analytics.cycles.retrain")
    # Actually observe is in verdict — this scheduler is oracle-only
    # In production the verdict scheduler handles observe; oracle handles learning cycles
    logger.info("ORACLE: T+1 observe cycle would be triggered (runs in VERDICT service)")


async def _observe_t7():
    logger.info("ORACLE: T+7 observe cycle would be triggered (runs in VERDICT service)")


async def _observe_t30():
    logger.info("ORACLE: T+30 observe cycle would be triggered (runs in VERDICT service)")


async def _attribute():
    logger.info("ORACLE: DR attribution cycle started")
    # In production, VERDICT's attribute.py runs this
    logger.info("ORACLE: DR attribution cycle complete (runs in VERDICT service)")


async def _refine():
    from .cycles.refine import run_daily_prompt_optimisation
    logger.info("ORACLE: REFINE cycle started")
    await run_daily_prompt_optimisation()


async def _route():
    from .cycles.route import update_channel_policy_from_uplift
    logger.info("ORACLE: ROUTE cycle started")
    await update_channel_policy_from_uplift()


async def _narrate():
    from .cycles.narrate import run_nightly_narration
    logger.info("ORACLE: NARRATE cycle started")
    cards = await run_nightly_narration()
    logger.info(f"ORACLE: NARRATE produced {len(cards)} insight cards")


async def _retrain():
    from .cycles.retrain import run_weekly_retrain
    logger.info("ORACLE: RETRAIN cycle started (weekly)")
    await run_weekly_retrain()


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

    # Prompt bandit update — daily 05:00
    scheduler.add_job(_refine, CronTrigger(hour=5, minute=0), id="refine")

    # Channel policy update — every hour
    scheduler.add_job(_route, IntervalTrigger(hours=1), id="route")

    # Nightly narration — 06:00
    scheduler.add_job(_narrate, CronTrigger(hour=6, minute=0), id="narrate")

    # Weekly CHRONOS retrain — Sunday 02:00
    scheduler.add_job(_retrain, CronTrigger(day_of_week="sun", hour=2, minute=0), id="retrain")

    return scheduler


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("ORACLE scheduler started. Press Ctrl+C to stop.")
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("ORACLE scheduler stopped.")


if __name__ == "__main__":
    asyncio.run(main())
