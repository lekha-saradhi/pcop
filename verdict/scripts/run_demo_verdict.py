"""
Demo script for VERDICT Layer 6.
Simulates T+30 outcome measurement and DR uplift attribution for a set of demo customers.

Usage:
    python scripts/run_demo_verdict.py
    python scripts/run_demo_verdict.py --window 7
    python scripts/run_demo_verdict.py --campaign camp-demo-001 --channel email
"""
import os
import asyncio
import argparse
import json
import logging
from datetime import date, datetime, timezone, timedelta

os.environ.setdefault("VERDICT_DEMO_MODE", "true")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("verdict_demo")


DEMO_CUSTOMERS = [
    {"customer_id": f"C-{i:08d}", "outreach_id": i, "holdout": i % 7 == 0}
    for i in range(1, 21)
]

DEMO_OUTCOME_SCENARIOS = [
    {"outcome_label": "retained", "churn_score_at_measure": 0.32, "score_reduction": 0.40, "signals_cleared": True},
    {"outcome_label": "partial", "churn_score_at_measure": 0.55, "score_reduction": 0.17, "signals_cleared": True},
    {"outcome_label": "unresponsive", "churn_score_at_measure": 0.78, "score_reduction": 0.01, "signals_cleared": False},
    {"outcome_label": "churned", "churn_score_at_measure": 0.91, "score_reduction": -0.05, "signals_cleared": False},
]


async def run_demo_observe(window_days: int):
    from services.measurement.nodes.observe import _derive_outcome_label

    logger.info(f"\n{'='*60}")
    logger.info(f"OBSERVE — T+{window_days} Outcome Measurement")
    logger.info(f"{'='*60}")

    results = []
    for i, customer in enumerate(DEMO_CUSTOMERS):
        scenario = DEMO_OUTCOME_SCENARIOS[i % len(DEMO_OUTCOME_SCENARIOS)]
        products_closed = 1 if scenario["outcome_label"] == "churned" else 0

        label = _derive_outcome_label(
            churn_score=scenario["churn_score_at_measure"],
            score_reduction=scenario["score_reduction"],
            products_closed=products_closed,
            signals_cleared=scenario["signals_cleared"],
        )

        result = {
            **customer,
            "window_days": window_days,
            "outcome_label": label,
            "score_reduction": scenario["score_reduction"],
            "signals_cleared": scenario["signals_cleared"],
        }
        results.append(result)
        logger.info(
            f"  {customer['customer_id']} "
            f"{'[holdout]' if customer['holdout'] else '[treatment]'} "
            f"→ {label:14s} "
            f"score_delta={scenario['score_reduction']:+.2f}"
        )

    label_counts = {}
    for r in results:
        label_counts[r["outcome_label"]] = label_counts.get(r["outcome_label"], 0) + 1

    logger.info(f"\nSummary: {label_counts}")
    return results


async def run_demo_attribute(campaign_id: str, channel: str):
    import numpy as np

    logger.info(f"\n{'='*60}")
    logger.info(f"ATTRIBUTE — DR Uplift: campaign={campaign_id} channel={channel}")
    logger.info(f"{'='*60}")

    rng = np.random.default_rng(seed=42)
    n = 120
    treatment_retained = 0.58
    holdout_retained = 0.43
    naive_uplift = treatment_retained - holdout_retained
    dr_uplift = naive_uplift * 0.82  # DR typically lower (removes selection bias)
    dr_se = 0.024
    bias = naive_uplift - dr_uplift

    logger.info(f"  n_treatment = 102 | n_holdout = 18")
    logger.info(f"  treatment retention rate = {treatment_retained:.1%}")
    logger.info(f"  holdout retention rate   = {holdout_retained:.1%}")
    logger.info(f"  naive uplift             = {naive_uplift:+.4f}")
    logger.info(f"  DR uplift                = {dr_uplift:+.4f} ± {dr_se:.4f}")
    logger.info(f"  overestimation bias      = {bias:+.4f}")
    logger.info(f"  CAUSAL-NET calibrated    = True (high_treat={dr_uplift+0.03:.4f} > low_treat={dr_uplift-0.04:.4f})")

    return {
        "campaign_id": campaign_id,
        "channel": channel,
        "naive_uplift": naive_uplift,
        "dr_uplift": dr_uplift,
        "dr_uplift_se": dr_se,
        "overestimation_bias": bias,
    }


async def main():
    parser = argparse.ArgumentParser(description="VERDICT Layer 6 demo")
    parser.add_argument("--window", type=int, default=30, choices=[1, 7, 30])
    parser.add_argument("--campaign", default="camp-demo-001")
    parser.add_argument("--channel", default="email")
    parser.add_argument("--output", default="demo_verdict_results.json")
    args = parser.parse_args()

    logger.info("VERDICT Layer 6 — Demo Mode")
    logger.info(f"Date: {date.today()} | Window: T+{args.window}")

    observe_results = await run_demo_observe(args.window)
    attribute_result = await run_demo_attribute(args.campaign, args.channel)

    output = {
        "run_date": date.today().isoformat(),
        "observation_window": args.window,
        "observe_results": observe_results,
        "attribute_result": attribute_result,
    }

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, default=str)

    logger.info(f"\nResults saved to {args.output}")
    logger.info(f"VERDICT demo complete.")


if __name__ == "__main__":
    asyncio.run(main())
