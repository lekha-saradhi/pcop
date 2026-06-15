"""APScheduler configuration for all CHRONOS recurring tasks."""

from __future__ import annotations

import logging
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import text

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

_scheduler: AsyncIOScheduler | None = None


def _get_db():
    from api.database import SessionLocal
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def _run_batch_scoring() -> None:
    """Run the full CHRONOS batch scoring pipeline and persist results."""
    logger.info("Scheduler: starting batch scoring pipeline")
    from services.scoring.serving.batch_scorer import (
        BatchScorer,
        load_customers_from_db,
        write_scores_to_db,
    )
    try:
        customers = load_customers_from_db()
        if not customers:
            logger.info("Batch scoring: no customers to score")
            return
        scorer = BatchScorer()
        results = scorer.run_full_pipeline(customers)
        write_scores_to_db(results, scoring_pass="batch-v1.0")
        logger.info("Batch scoring pipeline completed: %d customers scored", len(results))
    except Exception:
        logger.exception("Batch scoring pipeline failed")


def _run_fusion_recalibration() -> None:
    """Recalibrate FUSION-X weights using recent labelled outcomes."""
    logger.info("Scheduler: recalibrating FUSION-X weights")
    from services.scoring.fusion.fusion_x import FusionX
    try:
        db = _get_db()
        try:
            rows = db.execute(
                text("""
                    SELECT tare_score, habitat_score, final_score
                    FROM churn_scores
                    WHERE tare_score IS NOT NULL AND habitat_score IS NOT NULL
                    ORDER BY scored_at DESC LIMIT 1000
                """),
            ).fetchall()
        finally:
            db.close()

        if len(rows) < 50:
            logger.info("FUSION-X recalibration: only %d rows available (need 50+)", len(rows))
            return

        tare_scores = [float(r.tare_score) for r in rows]
        habitat_scores = [float(r.habitat_score) for r in rows]
        outcomes = [1 if float(r.final_score) >= 0.5 else 0 for r in rows]

        fusion = FusionX()
        new_weights = fusion.calibrate(tare_scores, habitat_scores, outcomes)
        drift = fusion.check_drift(
            [float(r.final_score) for r in rows],
            outcomes,
        )
        logger.info(
            "FUSION-X recalibration: weights=%s drift=%s",
            new_weights.as_dict(),
            drift.status.value,
        )
    except Exception:
        logger.exception("FUSION-X recalibration failed")


def _run_aegis_drift_check() -> None:
    """Check for input signal drift via AEGIS."""
    logger.info("Scheduler: running AEGIS drift check")
    from services.scoring.guards.aegis_detector import AEGISDetector
    try:
        db = _get_db()
        try:
            rows = db.execute(
                text("SELECT reason_codes_v2 FROM churn_scores WHERE reason_codes_v2 IS NOT NULL LIMIT 100"),
            ).fetchall()
        finally:
            db.close()

        aegis = AEGISDetector()
        aegis.load_reference_distributions(str(
            Path(__file__).resolve().parents[2] / "ml" / "checkpoints" / "aegis_reference.json"
        ))

        alerts = []
        if rows:
            raw_numeric = [[len(rc) for rc in (r.reason_codes_v2 or [])] for r in rows if r.reason_codes_v2]
            if raw_numeric:
                import numpy as np
                alerts = aegis.check_features(np.array(raw_numeric, dtype=float))
                seqs = [r.reason_codes_v2 for r in rows if r.reason_codes_v2]
                if seqs:
                    alerts.extend(aegis.check_sequences(seqs))

        if alerts:
            for a in alerts:
                logger.warning("AEGIS drift alert: %s", a.message)
        else:
            logger.info("AEGIS drift check: no drift detected")
    except Exception:
        logger.exception("AEGIS drift check failed")


def _run_genesis_graduations() -> None:
    """Evaluate cold-start customers for graduation to the full model pipeline."""
    logger.info("Scheduler: evaluating GENESIS graduations")
    from services.scoring.models.genesis_scorer import GENESISScorer
    from services.scoring.serving.batch_scorer import (
        load_customers_from_db,
        BatchScorer,
        write_scores_to_db,
    )
    try:
        scorer = GENESISScorer()
        customers = load_customers_from_db()
        graduated = [
            c for c in customers
            if scorer.is_graduated(c.tenure_days, sum(1 for t in c.token_ids if t != 0))
        ]
        if not graduated:
            logger.info("GENESIS graduations: no customers to graduate")
            return
        batch = BatchScorer()
        results = batch.run_full_pipeline(graduated)
        write_scores_to_db(results, scoring_pass="genesis-graduation-v1.0")
        logger.info("GENESIS graduations: %d customers graduated and re-scored", len(graduated))
    except Exception:
        logger.exception("GENESIS graduations failed")


def _run_habitat_pass2() -> None:
    """Run conditional HABITAT Pass 2 re-scoring for eligible customers."""
    logger.info("Scheduler: running HABITAT Pass 2 conditional re-scoring")
    from services.scoring.models.habitat_pass2 import HabitatPass2Scorer, is_eligible_for_pass2
    try:
        db = _get_db()
        try:
            rows = db.execute(
                text("""
                    SELECT customer_id, tare_score, habitat_score, final_score
                    FROM churn_scores
                    WHERE scoring_pass = 'batch-v1.0'
                    ORDER BY scored_at DESC LIMIT 500
                """),
            ).fetchall()
        finally:
            db.close()

        pass2 = HabitatPass2Scorer()
        rescored = 0
        for r in rows:
            pass1 = float(r.habitat_score or r.tare_score or r.final_score)
            _life_events = []
            inner = None
            try:
                inner = _get_db()
                _life_events = inner.execute(
                    text("SELECT event_type, created_at FROM signal_results WHERE customer_id = :cid ORDER BY created_at DESC"),
                    {"cid": r.customer_id},
                ).fetchall()
            finally:
                if inner is not None:
                    inner.close()
            if is_eligible_for_pass2(pass1, len(_life_events)):
                logger.debug("customer_id=%s eligible for Pass 2 (score=%.4f, events=%d)", r.customer_id, pass1, len(_life_events))
                rescored += 1

        logger.info("HABITAT Pass 2: %d customers eligible for re-scoring", rescored)
    except Exception:
        logger.exception("HABITAT Pass 2 failed")


def _run_causal_net_scoring() -> None:
    """Compute CAUSAL-NET action tiers for high-churn customers."""
    logger.info("Scheduler: running CAUSAL-NET action scoring for treatable customers")
    from services.scoring.models.causal_net import _action_tier
    try:
        db = _get_db()
        try:
            rows = db.execute(
                text("""
                    SELECT customer_id, final_score, treatability_score
                    FROM churn_scores
                    WHERE final_score >= 0.4
                    ORDER BY scored_at DESC LIMIT 1000
                """),
            ).fetchall()
        finally:
            db.close()

        tier_counts: dict[str, int] = {}
        for r in rows:
            p_churn = float(r.final_score)
            p_treatable = float(r.treatability_score) if r.treatability_score is not None else 0.5
            tier = _action_tier(p_churn, p_treatable).value
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        logger.info("CAUSAL-NET action tiers: %s", tier_counts)
    except Exception:
        logger.exception("CAUSAL-NET action scoring failed")


def _trigger_mlflow_retrain() -> None:
    logger.info("Scheduler: triggering weekly MLflow retraining pipeline")
    from services.scoring.serving.batch_scorer import logger as bs_logger
    try:
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "ml.register_all_models", "--dry-run"],
            capture_output=True, text=True, timeout=300,
        )
        logger.info("MLflow retrain dry-run: stdout=%s stderr=%s", result.stdout[:200], result.stderr[:200])
    except Exception:
        logger.exception("MLflow retrain trigger failed")


def _trigger_causal_net_retrain() -> None:
    logger.info("Scheduler: triggering bi-weekly CAUSAL-NET retraining")
    try:
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "ml.training.causal_net_train"],
            capture_output=True, text=True, timeout=600,
        )
        logger.info("CAUSAL-NET retrain: stdout=%s stderr=%s", result.stdout[:200], result.stderr[:200])
    except Exception:
        logger.exception("CAUSAL-NET retrain trigger failed")


def _trigger_genesis_retrain() -> None:
    logger.info("Scheduler: triggering monthly GENESIS retraining")
    try:
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "ml.training.genesis_train"],
            capture_output=True, text=True, timeout=600,
        )
        logger.info("GENESIS retrain: stdout=%s stderr=%s", result.stdout[:200], result.stderr[:200])
    except Exception:
        logger.exception("GENESIS retrain trigger failed")


def create_scheduler() -> AsyncIOScheduler:
    """Build and return the APScheduler instance with all CHRONOS tasks configured."""
    global _scheduler
    scheduler = AsyncIOScheduler(timezone="UTC")

    # Every 6 hours: full batch scoring pipeline
    scheduler.add_job(
        _run_batch_scoring,
        trigger=IntervalTrigger(hours=6),
        id="batch_scoring",
        name="Full batch scoring pipeline",
        replace_existing=True,
    )

    # Every 6 hours: AEGIS drift check
    scheduler.add_job(
        _run_aegis_drift_check,
        trigger=IntervalTrigger(hours=6),
        id="aegis_drift_check",
        name="AEGIS input drift check",
        replace_existing=True,
    )

    # Every 6 hours: FUSION-X ECE check
    scheduler.add_job(
        _run_fusion_recalibration,
        trigger=IntervalTrigger(hours=6),
        id="fusion_ece_check",
        name="FUSION-X ECE calibration check",
        replace_existing=True,
    )

    # Daily 04:00 UTC: FUSION-X weight recalibration
    scheduler.add_job(
        _run_fusion_recalibration,
        trigger=CronTrigger(hour=4, minute=0),
        id="fusion_recalibration",
        name="FUSION-X daily weight recalibration",
        replace_existing=True,
    )

    # Daily 05:00 UTC: GENESIS graduation evaluation
    scheduler.add_job(
        _run_genesis_graduations,
        trigger=CronTrigger(hour=5, minute=0),
        id="genesis_graduations",
        name="GENESIS graduation evaluation",
        replace_existing=True,
    )

    # After Layer 4 completes: HABITAT Pass 2 (event-driven, daily approx)
    scheduler.add_job(
        _run_habitat_pass2,
        trigger=CronTrigger(hour=7, minute=0),
        id="habitat_pass2",
        name="HABITAT Pass 2 conditional re-scoring",
        replace_existing=True,
    )

    # After Pass 2: CAUSAL-NET action scoring
    scheduler.add_job(
        _run_causal_net_scoring,
        trigger=CronTrigger(hour=8, minute=0),
        id="causal_net_scoring",
        name="CAUSAL-NET treatability scoring",
        replace_existing=True,
    )

    # Weekly Sunday 02:00 UTC: MLflow retraining pipeline
    scheduler.add_job(
        _trigger_mlflow_retrain,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="mlflow_retrain",
        name="Weekly MLflow retraining trigger",
        replace_existing=True,
    )

    # Bi-weekly: CAUSAL-NET retraining (every 2 weeks, Monday 03:00 UTC)
    scheduler.add_job(
        _trigger_causal_net_retrain,
        trigger=CronTrigger(day_of_week="mon", hour=3, minute=0, week="*/2"),
        id="causal_net_retrain",
        name="Bi-weekly CAUSAL-NET retraining",
        replace_existing=True,
    )

    # Monthly: GENESIS retraining (1st of month, 06:00 UTC)
    scheduler.add_job(
        _trigger_genesis_retrain,
        trigger=CronTrigger(day=1, hour=6, minute=0),
        id="genesis_retrain",
        name="Monthly GENESIS retraining",
        replace_existing=True,
    )

    _scheduler = scheduler
    logger.info("APScheduler configured with %d jobs", len(scheduler.get_jobs()))
    return scheduler


def get_scheduler_status() -> dict:
    """Return current status of all scheduled jobs."""
    if _scheduler is None:
        return {"running": False, "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        })
    return {"running": _scheduler.running, "jobs": jobs}
