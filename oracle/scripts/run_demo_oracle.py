"""
Demo script for ORACLE Layer 7.
Simulates all four ORACLE cycles: RETRAIN, REFINE, ROUTE, NARRATE.

Usage:
    python scripts/run_demo_oracle.py
    python scripts/run_demo_oracle.py --cycle narrate
    python scripts/run_demo_oracle.py --cycle refine
"""
import os
import asyncio
import argparse
import json
import logging
from datetime import date

os.environ.setdefault("ORACLE_DEMO_MODE", "true")
os.environ.setdefault("MLFLOW_TRACKING_URI", "")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("oracle_demo")


async def demo_retrain():
    logger.info("\n" + "=" * 60)
    logger.info("CYCLE 1: RETRAIN — CHRONOS Weekly Model Retraining")
    logger.info("=" * 60)

    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(42)
    n = 500
    dr_uplifts = rng.uniform(-0.05, 0.15, n)
    train_df = pd.DataFrame({
        "customer_id": [f"C-{i:08d}" for i in range(n)],
        "churn_label": rng.integers(0, 2, n),
        "dr_uplift": dr_uplifts,
        "sample_weight": np.clip(dr_uplifts / 0.15, 0.3, 1.0),
    })

    logger.info(f"  Training samples: {len(train_df)}")
    logger.info(f"  Churn rate: {train_df['churn_label'].mean():.1%}")
    logger.info(f"  DR-weighted samples (weight>0.5): {int((train_df['sample_weight'] > 0.5).sum())}")
    logger.info(f"  CAUSAL-NET calibration: OK — retraining skipped")
    logger.info(f"  TARE: retrained (GRU encoder, DR-weighted labels)")
    logger.info(f"  HABITAT: retrained (XGBoost, DR-weighted labels)")
    logger.info(f"  FUSION-X: weights recalibrated")
    logger.info(f"  AEGIS: reference distributions updated")
    logger.info(f"  MLflow run: weekly_retrain_{date.today()}")


async def demo_refine():
    logger.info("\n" + "=" * 60)
    logger.info("CYCLE 2: REFINE — Prompt Bandit Update & A/B Test")
    logger.info("=" * 60)

    versions = [
        {"version_id": "email_v1", "dr_uplift": 0.082, "new_obs": 15, "alpha": 8, "beta": 4},
        {"version_id": "email_v2", "dr_uplift": 0.031, "new_obs": 12, "alpha": 5, "beta": 6},
        {"version_id": "sms_v1", "dr_uplift": 0.045, "new_obs": 8, "alpha": 6, "beta": 5},
    ]

    for v in versions:
        uplift_fraction = max(0.0, min(1.0, v["dr_uplift"] / 0.10))
        successes = int(round(v["new_obs"] * uplift_fraction))
        failures = v["new_obs"] - successes
        new_alpha = v["alpha"] + successes
        new_beta = v["beta"] + failures
        expected_rate = new_alpha / (new_alpha + new_beta)
        logger.info(
            f"  {v['version_id']}: dr_uplift={v['dr_uplift']:.4f} "
            f"successes={successes} failures={failures} "
            f"expected_rate={expected_rate:.3f}"
        )

    logger.info(f"\n  A/B Test (email): a_retained=45/80 vs b_retained=62/80")
    from scipy.stats import fisher_exact
    _, p = fisher_exact([[45, 35], [62, 18]], alternative="two-sided")
    winner = "B" if p < 0.05 else "no winner yet"
    logger.info(f"  Fisher's exact p={p:.4f} → winner={winner}")


async def demo_route():
    logger.info("\n" + "=" * 60)
    logger.info("CYCLE 3: ROUTE — Channel Policy Bayesian Update")
    logger.info("=" * 60)

    cells = [
        {"segment": "mass_affluent", "tier": "high", "strategy": "full_retention"},
        {"segment": "mass_affluent", "tier": "medium", "strategy": "proactive"},
    ]
    channels = [
        {"channel": "email", "dr_uplift": 0.07, "n": 45},
        {"channel": "app", "dr_uplift": 0.09, "n": 38},
        {"channel": "sms", "dr_uplift": 0.03, "n": 30},
    ]

    for cell in cells:
        logger.info(f"\n  Cell: {cell['segment']} × {cell['tier']} × {cell['strategy']}")
        for ch in channels:
            successes = max(0, int(ch["n"] * ch["dr_uplift"]))
            logger.info(
                f"    {ch['channel']}: dr_uplift={ch['dr_uplift']:.3f} "
                f"α+={successes} β+={ch['n']-successes}"
            )


async def demo_narrate():
    logger.info("\n" + "=" * 60)
    logger.info("CYCLE 4: NARRATE — LLM Insight Generation (DeepSeek-V3)")
    logger.info("=" * 60)

    demo_cards = [
        {
            "severity": "high",
            "title": "ARGUS alarm volume surged +38% in Mass Affluent segment",
            "what": "ARGUS alarm count rose from 612 to 847 over 7 days",
            "why": "TEMPO transaction frequency signal breaching 2σ control limits for 847 customers",
            "where": "Mass Affluent segment, Mumbai and Delhi markets",
            "recommend": "Increase COMPASS dispatch capacity; review WARDEN FDR threshold reduction",
            "metric_name": "argus_alarm_count",
            "metric_delta": "+38.4%",
            "affected_customers": 847,
        },
        {
            "severity": "high",
            "title": "HERALD SENTINEL SMS failure rate spiked +72%",
            "what": "SMS compliance failure rate increased from 1.8% to 3.1%",
            "why": "Likely new prohibited phrase pattern in sms_v2 prompt template",
            "where": "SMS channel, all segments",
            "recommend": "Audit SMS prompt_version sms_v2; update PROHIBITED_PHRASES list",
            "metric_name": "sentinel_failure_rate",
            "metric_delta": "+72.2%",
            "affected_customers": 143,
        },
        {
            "severity": "info",
            "title": "Email DR uplift improved +26% vs prior week",
            "what": "DR-estimated email channel uplift rose from 6.5% to 8.2%",
            "why": "Likely due to prompt_version email_v1 Thompson bandit gaining weight after A/B winner promotion",
            "where": "Email channel, Mass Affluent segment, high-risk tier",
            "recommend": "Continue current email_v1 prompt; monitor graceful_retention strategy performance",
            "metric_name": "dr_uplift_email",
            "metric_delta": "+26.2%",
            "affected_customers": None,
        },
    ]

    for card in demo_cards:
        logger.info(f"\n  [{card['severity'].upper()}] {card['title']}")
        logger.info(f"    WHAT: {card['what']}")
        logger.info(f"    WHY:  {card['why']}")
        logger.info(f"    WHERE:{card['where']}")
        logger.info(f"    REC:  {card['recommend']}")

    logger.info(f"\n  {len(demo_cards)} insight cards → pcop.insights.v1 (Kafka)")
    return demo_cards


async def main():
    parser = argparse.ArgumentParser(description="ORACLE Layer 7 demo")
    parser.add_argument("--cycle", choices=["all", "retrain", "refine", "route", "narrate"], default="all")
    parser.add_argument("--output", default="demo_oracle_results.json")
    args = parser.parse_args()

    logger.info("ORACLE Layer 7 — Demo Mode")
    logger.info(f"Date: {date.today()} | Cycle: {args.cycle}")

    results = {}

    if args.cycle in ("all", "retrain"):
        await demo_retrain()
        results["retrain"] = "complete"

    if args.cycle in ("all", "refine"):
        await demo_refine()
        results["refine"] = "complete"

    if args.cycle in ("all", "route"):
        await demo_route()
        results["route"] = "complete"

    if args.cycle in ("all", "narrate"):
        cards = await demo_narrate()
        results["narrate"] = {"cards": cards}

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"\nResults saved to {args.output}")
    logger.info("ORACLE demo complete.")


if __name__ == "__main__":
    asyncio.run(main())
