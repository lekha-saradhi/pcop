"""
Runs HERALD for 20 demo action plan events (COMPASS Layer 4 output).
No Kafka required. Direct graph invocation.
Prints a summary table at the end.

Usage:
  python scripts/run_demo_herald.py
  python scripts/run_demo_herald.py --customer C-00000001
  python scripts/run_demo_herald.py --dry-run
"""

import asyncio
import argparse
import json
import os
from datetime import date

os.environ.setdefault("HERALD_DEMO_MODE", "true")

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.content.graph.builder import build_herald_graph

DEMO_ACTION_PLANS = [
    {
        "customer_id": "C-00000001",
        "outreach_id": 1001,
        "risk_tier": "critical",
        "final_score": 0.87,
        "action_score": 0.52,
        "final_events": [
            {"event_type": "job_change", "confidence": 0.91, "evidence": ["Employer: TCS→Infosys", "+22% salary"], "source": "llm_cognition"},
            {"event_type": "relocation", "confidence": 0.88, "evidence": ["Bangalore 68% dominance in last 30d"], "source": "rule_verify"},
        ],
        "action_plan": {
            "channel": "email",
            "offer_code": "MA_RATE_UPGRADE",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "system",
            "priority": 1,
            "rationale": "Job change + relocation. Email with rate upgrade.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000002",
        "outreach_id": 1002,
        "risk_tier": "high",
        "final_score": 0.74,
        "action_score": 0.44,
        "final_events": [],
        "action_plan": {
            "channel": "app",
            "offer_code": "MA_CASHBACK_6M",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "system",
            "priority": 2,
            "rationale": "Engagement drop. In-app reengagement push.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000003",
        "outreach_id": 1003,
        "risk_tier": "high",
        "final_score": 0.71,
        "action_score": 0.41,
        "final_events": [
            {"event_type": "financial_stress", "confidence": 0.83, "evidence": ["CFSI elevated 3 weeks"], "source": "rule_verify"},
        ],
        "action_plan": {
            "channel": "call",
            "offer_code": "STRESS_RELIEF_EMI",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "rm_team",
            "priority": 2,
            "rationale": "Financial stress. Empathetic call with EMI relief.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000004",
        "outreach_id": 1004,
        "risk_tier": "medium",
        "final_score": 0.55,
        "action_score": 0.38,
        "final_events": [
            {"event_type": "marriage", "confidence": 0.88, "evidence": ["MCC 5944 (jewellery)", "MCC 7011 (hotel)"], "source": "rule_verify"},
        ],
        "action_plan": {
            "channel": "email",
            "offer_code": "MARRIAGE_BUNDLE",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "system",
            "priority": 2,
            "rationale": "Marriage detected. Celebratory email with wedding bundle.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000005",
        "outreach_id": 1005,
        "risk_tier": "low",
        "final_score": 0.35,
        "action_score": 0.22,
        "final_events": [],
        "action_plan": {
            "channel": None,
            "offer_code": None,
            "timing": None,
            "owner_id": "system",
            "priority": 5,
            "rationale": "Monitor only. Low risk, no intervention.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000006",
        "outreach_id": 1006,
        "risk_tier": "critical",
        "final_score": 0.91,
        "action_score": 0.58,
        "final_events": [
            {"event_type": "bereavement", "confidence": 0.95, "evidence": ["MCC 7261 (funeral)", "MCC 8111 (legal)"], "source": "rule_verify"},
        ],
        "action_plan": {
            "channel": "rm_visit",
            "offer_code": "BEREAVEMENT_SUPPORT",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "senior_rm",
            "priority": 1,
            "rationale": "Bereavement confirmed. Sensitive RM visit with estate support.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000007",
        "outreach_id": 1007,
        "risk_tier": "high",
        "final_score": 0.72,
        "action_score": 0.43,
        "final_events": [
            {"event_type": "home_purchase", "confidence": 0.86, "evidence": ["MCC 6552 (real estate)"], "source": "rule_verify"},
        ],
        "action_plan": {
            "channel": "email",
            "offer_code": "HOME_LOAN_OFFER",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "system",
            "priority": 2,
            "rationale": "Home purchase. Home loan pre-approval email.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000008",
        "outreach_id": 1008,
        "risk_tier": "high",
        "final_score": 0.68,
        "action_score": 0.40,
        "final_events": [
            {"event_type": "retirement", "confidence": 0.82, "evidence": ["Salary cessation", "Pension credit started"], "source": "rule_verify"},
        ],
        "action_plan": {
            "channel": "call",
            "offer_code": "RETIREMENT_INCOME",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "rm_team",
            "priority": 2,
            "rationale": "Retirement. Call with senior citizen FD offer.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000009",
        "outreach_id": 1009,
        "risk_tier": "high",
        "final_score": 0.70,
        "action_score": 0.42,
        "final_events": [
            {"event_type": "new_baby", "confidence": 0.80, "evidence": ["MCC 5999 (baby products)", "MCC 8011 (paediatric)"], "source": "rule_verify"},
        ],
        "action_plan": {
            "channel": "email",
            "offer_code": "BABY_SAVINGS_PLAN",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "system",
            "priority": 2,
            "rationale": "New baby. Celebratory email with child savings plan.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000010",
        "outreach_id": 1010,
        "risk_tier": "critical",
        "final_score": 0.94,
        "action_score": 0.61,
        "final_events": [
            {"event_type": "churn_intent", "confidence": 0.77, "evidence": ["CRM: customer mentioned switching"], "source": "llm_cognition"},
        ],
        "action_plan": {
            "channel": "rm_visit",
            "offer_code": "HNW_RM_UPGRADE",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "senior_rm",
            "priority": 1,
            "rationale": "Explicit churn intent. Urgent RM visit.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000011",
        "outreach_id": 1011,
        "risk_tier": "medium",
        "final_score": 0.58,
        "action_score": 0.35,
        "final_events": [
            {"event_type": "salary_change", "confidence": 0.76, "evidence": ["Salary +12%"], "source": "rule_verify"},
        ],
        "action_plan": {
            "channel": "sms",
            "offer_code": "MA_RATE_UPGRADE",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "system",
            "priority": 3,
            "rationale": "Salary increase. Brief SMS with rate upgrade.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000012",
        "outreach_id": 1012,
        "risk_tier": "high",
        "final_score": 0.73,
        "action_score": 0.44,
        "final_events": [
            {"event_type": "relocation", "confidence": 0.84, "evidence": ["Chennai 72% dominance"], "source": "rule_verify"},
        ],
        "action_plan": {
            "channel": "email",
            "offer_code": "MA_RATE_UPGRADE",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "system",
            "priority": 2,
            "rationale": "Relocation to Chennai. Branch reassignment + offer.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000013",
        "outreach_id": 1013,
        "risk_tier": "high",
        "final_score": 0.69,
        "action_score": 0.41,
        "final_events": [
            {"event_type": "financial_stress", "confidence": 0.71, "evidence": ["CFSI borderline", "1 overdraft"], "source": "rule_verify"},
        ],
        "action_plan": {
            "channel": "app",
            "offer_code": "STRESS_RELIEF_EMI",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "system",
            "priority": 2,
            "rationale": "Stress + engagement drop. Supportive in-app.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000014",
        "outreach_id": 1014,
        "risk_tier": "low",
        "final_score": 0.38,
        "action_score": 0.24,
        "final_events": [],
        "action_plan": {
            "channel": None,
            "offer_code": None,
            "timing": None,
            "owner_id": "system",
            "priority": 5,
            "rationale": "Monitor only.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000015",
        "outreach_id": 1015,
        "risk_tier": "critical",
        "final_score": 0.93,
        "action_score": 0.60,
        "final_events": [
            {"event_type": "salary_change", "confidence": 0.80, "evidence": ["Salary CUSUM at threshold"], "source": "rule_verify"},
        ],
        "action_plan": {
            "channel": "rm_visit",
            "offer_code": "HNW_FEE_WAIVER_12M",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "senior_rm",
            "priority": 1,
            "rationale": "4 signals co-firing. Critical RM intervention.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000016",
        "outreach_id": 1016,
        "risk_tier": "high",
        "final_score": 0.67,
        "action_score": 0.40,
        "final_events": [
            {"event_type": "marriage", "confidence": 0.78, "evidence": ["MCC 5944", "MCC 5947"], "source": "rule_verify"},
        ],
        "action_plan": {
            "channel": "email",
            "offer_code": "MARRIAGE_BUNDLE",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "system",
            "priority": 2,
            "rationale": "Marriage detected. Wedding bundle email.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000017",
        "outreach_id": 1017,
        "risk_tier": "medium",
        "final_score": 0.52,
        "action_score": 0.32,
        "final_events": [],
        "action_plan": {
            "channel": "app",
            "offer_code": "MM_CASHBACK_3M",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "system",
            "priority": 3,
            "rationale": "Engagement drop. In-app reengagement.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000018",
        "outreach_id": 1018,
        "risk_tier": "high",
        "final_score": 0.71,
        "action_score": 0.43,
        "final_events": [
            {"event_type": "home_purchase", "confidence": 0.81, "evidence": ["MCC 6552", "MCC 5211"], "source": "rule_verify"},
            {"event_type": "financial_stress", "confidence": 0.74, "evidence": ["CFSI elevated post purchase"], "source": "rule_verify"},
        ],
        "action_plan": {
            "channel": "call",
            "offer_code": "HOME_LOAN_OFFER",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "rm_team",
            "priority": 2,
            "rationale": "Home purchase + post-purchase stress. Supportive call.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000019",
        "outreach_id": 1019,
        "risk_tier": "low",
        "final_score": 0.40,
        "action_score": 0.26,
        "final_events": [],
        "action_plan": {
            "channel": None,
            "offer_code": None,
            "timing": None,
            "owner_id": "system",
            "priority": 5,
            "rationale": "Monitor only. Mild sentiment dip.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
    {
        "customer_id": "C-00000020",
        "outreach_id": 1020,
        "risk_tier": "medium",
        "final_score": 0.57,
        "action_score": 0.36,
        "final_events": [
            {"event_type": "salary_change", "confidence": 0.73, "evidence": ["Salary +8%"], "source": "rule_verify"},
            {"event_type": "marriage", "confidence": 0.82, "evidence": ["MCC 5944", "MCC 7011", "MCC 5947"], "source": "rule_verify"},
        ],
        "action_plan": {
            "channel": "email",
            "offer_code": "MARRIAGE_BUNDLE",
            "timing": f"{date.today()}T09:00:00",
            "owner_id": "system",
            "priority": 2,
            "rationale": "Salary increase + marriage. Celebratory email.",
        },
        "dispatch_timestamp": f"{date.today()}T06:00:00Z",
    },
]


async def run_single(graph, action_plan_event: dict, dry_run: bool = False) -> dict:
    customer_id = action_plan_event["customer_id"]
    channel = (action_plan_event.get("action_plan") or {}).get("channel")

    if not channel:
        return {"customer_id": customer_id, "skipped": True, "reason": "monitor_plan"}

    if dry_run:
        print(f"[DRY RUN] Would process {customer_id} via {channel}")
        return {"customer_id": customer_id, "dry_run": True}

    initial_state = {
        "action_plan_event": action_plan_event,
        "customer_id": customer_id,
        "channel": channel,
        "brief": None,
        "generated_content": None,
        "ab_variant": None,
        "compliance_status": None,
        "compliance_notes": None,
        "retry_count": 0,
        "dispatched": False,
        "dispatch_provider_id": None,
        "content_store_id": None,
        "human_review_required": False,
    }

    return await graph.ainvoke(initial_state)


async def main():
    parser = argparse.ArgumentParser(description="HERALD demo runner")
    parser.add_argument("--customer", help="Process single customer ID only")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    graph = build_herald_graph()
    plans = DEMO_ACTION_PLANS

    if args.customer:
        plans = [p for p in DEMO_ACTION_PLANS if p["customer_id"] == args.customer]
        if not plans:
            print(f"Customer {args.customer} not found in demo data")
            return

    print(f"\nRunning HERALD demo for {len(plans)} action plans...\n")
    print(f"{'Customer':<16} {'Channel':<10} {'Compliance':<14} {'Dispatched':<12} {'ContentID':<10}")
    print("-" * 72)

    results = []
    for plan in plans:
        customer_id = plan["customer_id"]
        try:
            result = await run_single(graph, plan, args.dry_run)
            results.append(result)

            if result.get("skipped"):
                print(f"{customer_id:<16} {'—':<10} {'SKIPPED':<14} {'—':<12} {'—':<10}")
            elif result.get("dry_run"):
                print(f"{customer_id:<16} {plan['action_plan'].get('channel','—'):<10} {'DRY RUN':<14} {'—':<12} {'—':<10}")
            else:
                print(
                    f"{customer_id:<16} "
                    f"{result.get('channel', '—'):<10} "
                    f"{result.get('compliance_status', 'n/a'):<14} "
                    f"{str(result.get('dispatched', False)):<12} "
                    f"{str(result.get('content_store_id', '—')):<10}"
                )
        except Exception as e:
            print(f"{customer_id:<16} ERROR: {e}")

    print(f"\nCompleted {len(results)} action plans.")

    output_path = "demo_herald_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
