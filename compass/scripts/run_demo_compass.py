"""
Runs COMPASS for all 20 dummy customers from Chapter 6.
No Kafka required. Direct graph invocation.
Prints a summary table at the end.

Usage:
  python scripts/run_demo_compass.py
  python scripts/run_demo_compass.py --customer C-00000001
  python scripts/run_demo_compass.py --dry-run
"""

import asyncio
import argparse
import json
from datetime import date

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.orchestration.graph.builder import build_demo_graph
from services.orchestration.state import CompassState

DEMO_CUSTOMERS = [
    {
        "customer_id": "C-00000001",
        "alarm_severity": "CRITICAL",
        "signal_results": [
            {"signal_type": "cusum_salary", "detected": True, "confidence": 0.85,
             "evidence": ["Employer ref changed: TCS→Infosys", "Amount +22%"],
             "direction": "increase", "onset_estimate": "2024-09-01",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
            {"signal_type": "location_rule", "detected": True, "confidence": 0.91,
             "evidence": ["Bangalore dominant 68% in last 30d", "Mumbai <10%"],
             "direction": None, "onset_estimate": "2024-10-01",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
            {"signal_type": "beta_cusum_sentiment", "detected": True, "confidence": 0.72,
             "evidence": ["Sentiment declining: 3 complaints unresolved"],
             "direction": "decrease", "onset_estimate": "2024-08-20",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000002",
        "alarm_severity": "HIGH",
        "signal_results": [
            {"signal_type": "ewma_engagement", "detected": True, "confidence": 0.78,
             "evidence": ["Login frequency -65% vs baseline", "Last login 14d ago"],
             "direction": "decrease", "onset_estimate": "2024-10-15",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
            {"signal_type": "sr_transaction", "detected": True, "confidence": 0.71,
             "evidence": ["Transaction frequency declining for 6 weeks"],
             "direction": "decrease", "onset_estimate": "2024-09-20",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000003",
        "alarm_severity": "HIGH",
        "signal_results": [
            {"signal_type": "cfsi_stress", "detected": True, "confidence": 0.83,
             "evidence": ["CFSI composite elevated 3 consecutive weeks", "Overdraft +4 events"],
             "direction": "increase", "onset_estimate": "2024-10-05",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000004",
        "alarm_severity": "MEDIUM",
        "signal_results": [
            {"signal_type": "lifecycle_mcc_marriage", "detected": True, "confidence": 0.88,
             "evidence": ["MCC 5944 (jewellery)", "MCC 7011 (hotel)", "MCC 5947 (gifts)"],
             "direction": None, "onset_estimate": "2024-10-10",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000005",
        "alarm_severity": "LOW",
        "signal_results": [
            {"signal_type": "sa_ewma_recency", "detected": True, "confidence": 0.55,
             "evidence": ["Recency score declining gently"],
             "direction": "decrease", "onset_estimate": "2024-10-20",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000006",
        "alarm_severity": "CRITICAL",
        "signal_results": [
            {"signal_type": "nexus_correlation", "detected": True, "confidence": 0.88,
             "evidence": ["Joint alarm: 3 signals co-firing", "LRT p=0.003"],
             "direction": None, "onset_estimate": "2024-10-28",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
            {"signal_type": "lifecycle_mcc_bereavement", "detected": True, "confidence": 0.95,
             "evidence": ["MCC 7261 (funeral services) detected", "MCC 8111 (legal)"],
             "direction": None, "onset_estimate": "2024-10-25",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000007",
        "alarm_severity": "HIGH",
        "signal_results": [
            {"signal_type": "lifecycle_mcc_home", "detected": True, "confidence": 0.86,
             "evidence": ["MCC 6552 (real estate)", "MCC 8111 (legal conveyancing)"],
             "direction": None, "onset_estimate": "2024-10-15",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000008",
        "alarm_severity": "HIGH",
        "signal_results": [
            {"signal_type": "lifecycle_mcc_retirement", "detected": True, "confidence": 0.82,
             "evidence": ["Salary credit cessation", "Pension credit started"],
             "direction": None, "onset_estimate": "2024-09-30",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000009",
        "alarm_severity": "HIGH",
        "signal_results": [
            {"signal_type": "lifecycle_mcc_baby", "detected": True, "confidence": 0.80,
             "evidence": ["MCC 5999 (baby products)", "MCC 8011 (paediatric)"],
             "direction": None, "onset_estimate": "2024-10-01",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000010",
        "alarm_severity": "CRITICAL",
        "signal_results": [
            {"signal_type": "oracle_multivariate", "detected": True, "confidence": 0.94,
             "evidence": ["Joint multivariate alarm p<0.001", "5 signals elevated"],
             "direction": None, "onset_estimate": "2024-10-27",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
            {"signal_type": "beta_cusum_sentiment", "detected": True, "confidence": 0.77,
             "evidence": ["CRM note: customer mentioned switching banks"],
             "direction": "decrease", "onset_estimate": "2024-10-20",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000011",
        "alarm_severity": "MEDIUM",
        "signal_results": [
            {"signal_type": "cusum_salary", "detected": True, "confidence": 0.76,
             "evidence": ["Salary amount drifting +12%"],
             "direction": "increase", "onset_estimate": "2024-10-05",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000012",
        "alarm_severity": "HIGH",
        "signal_results": [
            {"signal_type": "location_rule", "detected": True, "confidence": 0.84,
             "evidence": ["Chennai dominant 72% in last 30d", "Hyderabad <5%"],
             "direction": None, "onset_estimate": "2024-10-08",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000013",
        "alarm_severity": "HIGH",
        "signal_results": [
            {"signal_type": "cfsi_stress", "detected": True, "confidence": 0.71,
             "evidence": ["CFSI borderline elevated", "1 overdraft event"],
             "direction": "increase", "onset_estimate": "2024-10-18",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
            {"signal_type": "ewma_engagement", "detected": True, "confidence": 0.68,
             "evidence": ["App usage down 40%"],
             "direction": "decrease", "onset_estimate": "2024-10-10",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000014",
        "alarm_severity": "LOW",
        "signal_results": [
            {"signal_type": "sr_transaction", "detected": True, "confidence": 0.60,
             "evidence": ["Transaction volume down 20%"],
             "direction": "decrease", "onset_estimate": "2024-10-12",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000015",
        "alarm_severity": "CRITICAL",
        "signal_results": [
            {"signal_type": "nexus_correlation", "detected": True, "confidence": 0.91,
             "evidence": ["4 signals co-firing simultaneously"],
             "direction": None, "onset_estimate": "2024-10-29",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
            {"signal_type": "cusum_salary", "detected": True, "confidence": 0.80,
             "evidence": ["Salary amount CUSUM at threshold"],
             "direction": "decrease", "onset_estimate": "2024-10-01",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000016",
        "alarm_severity": "HIGH",
        "signal_results": [
            {"signal_type": "lifecycle_mcc_marriage", "detected": True, "confidence": 0.78,
             "evidence": ["MCC 5944 (jewellery)", "MCC 5947 (gifts)"],
             "direction": None, "onset_estimate": "2024-10-22",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
            {"signal_type": "location_rule", "detected": True, "confidence": 0.65,
             "evidence": ["Pune shows moderate activity"],
             "direction": None, "onset_estimate": "2024-10-22",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000017",
        "alarm_severity": "MEDIUM",
        "signal_results": [
            {"signal_type": "ewma_engagement", "detected": True, "confidence": 0.62,
             "evidence": ["Login frequency down 30%"],
             "direction": "decrease", "onset_estimate": "2024-10-17",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000018",
        "alarm_severity": "HIGH",
        "signal_results": [
            {"signal_type": "lifecycle_mcc_home", "detected": True, "confidence": 0.81,
             "evidence": ["MCC 6552 (real estate)", "MCC 5211 (home improvement)"],
             "direction": None, "onset_estimate": "2024-10-14",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
            {"signal_type": "cfsi_stress", "detected": True, "confidence": 0.74,
             "evidence": ["CFSI elevated post home purchase"],
             "direction": "increase", "onset_estimate": "2024-10-14",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000019",
        "alarm_severity": "LOW",
        "signal_results": [
            {"signal_type": "beta_cusum_sentiment", "detected": True, "confidence": 0.58,
             "evidence": ["Sentiment mildly negative in last note"],
             "direction": "decrease", "onset_estimate": "2024-10-25",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
    {
        "customer_id": "C-00000020",
        "alarm_severity": "MEDIUM",
        "signal_results": [
            {"signal_type": "cusum_salary", "detected": True, "confidence": 0.73,
             "evidence": ["Salary amount drifting +8%"],
             "direction": "increase", "onset_estimate": "2024-10-01",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
            {"signal_type": "lifecycle_mcc_marriage", "detected": True, "confidence": 0.82,
             "evidence": ["MCC 5944 (jewellery), MCC 7011 (hotel), MCC 5947 (gifts)"],
             "direction": None, "onset_estimate": "2024-10-10",
             "cusum_value": None, "alarm_threshold": None, "expires_at": None},
        ],
    },
]


async def run_single_customer(graph, customer_data: dict, dry_run: bool = False) -> dict:
    initial_state: CompassState = {
        "customer_id": customer_data["customer_id"],
        "as_of_date": str(date.today()),
        "alarm_severity": customer_data["alarm_severity"],
        "alarm_timestamp": f"{date.today()}T06:00:00Z",
        "signal_results": customer_data["signal_results"],
        "risk_tier": None,
        "final_score": None,
        "action_score": None,
        "confirmed_events": [],
        "llm_inferred_events": [],
        "final_events": [],
        "risk_adjustment": 0.0,
        "action_plan": None,
        "gate_decision": None,
        "gate_reason": None,
        "dispatch_timestamp": None,
        "outreach_id": None,
    }

    if dry_run:
        print(f"[DRY RUN] Would process {customer_data['customer_id']}")
        return {"customer_id": customer_data["customer_id"], "dry_run": True}

    result = await graph.ainvoke(initial_state)
    return result


async def main():
    parser = argparse.ArgumentParser(description="COMPASS demo runner")
    parser.add_argument("--customer", help="Process single customer ID only")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be processed without running")
    args = parser.parse_args()

    graph = build_demo_graph()
    customers = DEMO_CUSTOMERS

    if args.customer:
        customers = [c for c in DEMO_CUSTOMERS if c["customer_id"] == args.customer]
        if not customers:
            print(f"Customer {args.customer} not found in demo data")
            return

    print(f"\nRunning COMPASS demo for {len(customers)} customers...\n")
    print(f"{'Customer':<16} {'Tier':<10} {'Events':<32} {'Gate':<12} {'Channel':<12}")
    print("-" * 92)

    results = []
    for customer_data in customers:
        try:
            result = await run_single_customer(graph, customer_data, args.dry_run)
            results.append(result)

            if not args.dry_run:
                events = [e["event_type"] for e in result.get("final_events", [])]
                print(
                    f"{result['customer_id']:<16} "
                    f"{result.get('risk_tier', 'n/a'):<10} "
                    f"{', '.join(events) or 'none':<32} "
                    f"{result.get('gate_decision', 'n/a'):<12} "
                    f"{result.get('action_plan', {}).get('channel') or 'none':<12}"
                )
        except Exception as e:
            print(f"{customer_data['customer_id']:<16} ERROR: {e}")

    print(f"\nCompleted {len(results)} customers.")

    output_path = "demo_compass_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
