"""
End-to-end smoke test using the dummy events from the spec.

Runs all 9 agents + the BOCPD joint detector against the dummy event
stream for customer C-00000001 (Arjun Sharma) and prints the emitted
SignalResults and Kafka alarm envelopes.

Run from repo root:
    PYTHONPATH=. python services/detection/demo.py
"""
import json
from datetime import datetime, timezone

from .agents import (
    SalaryAgent, LocationAgent, ComplaintSentimentAgent, ComplaintVolumeAgent,
    EngagementAgent, TransactionDriftAgent, StressAgent, LifecycleAgent,
    FeatureUsageAgent,
)
from .common.base_agent import (
    DictBaselineProvider, ListSink, signal_result_to_alarm,
)
from .common.schemas import Baseline, CanonicalEvent
from .common.state_store import InMemoryStateStore
from .joint_detector.bocpd_joint import BocpdJointDetector


CUSTOMER = "C-00000001"

# 1. Baselines for this customer (from bootstrap state in dummy input)
BASELINES = {
    CUSTOMER: {
        "salary_amount": Baseline(mu_0=148500.0, sigma=4200.0,
                                  computed_from="2024-01-01 to 2024-06-30"),
        "transaction_frequency_daily": Baseline(mu_0=8.4, sigma=2.1),
        "engagement_score": Baseline(mu_0=0.72, sigma=0.08),
        "overdraft_rate_monthly": Baseline(mu_0=0.02, sigma=0.01),
        "complaint_sentiment": Baseline(mu_0=0.15, sigma=0.20),
        "complaint_count_monthly": Baseline(mu_0=0.3, sigma=0.0, lambda_0=0.3),
    }
}


# 2. Dummy events in chronological order
EVENTS = [
    # ---- pcop.salary_credits.v1 ----
    {"event_id": "a1b2c3d4-0001", "customer_id": CUSTOMER, "event_type": "transaction",
     "event_timestamp": "2024-07-01T09:15:00Z", "source_system": "core_banking",
     "payload": {"txn_id": 50001, "amount": 148500.0, "direction": "credit",
                 "category": "salary_credit", "payment_ref": "TATA CONSULTANCY",
                 "merchant_city": "Mumbai", "txn_date": "2024-07-01",
                 "balance_after": 215400.0},
     "schema_version": "1.0"},
    {"event_id": "a1b2c3d4-0002", "customer_id": CUSTOMER, "event_type": "transaction",
     "event_timestamp": "2024-08-01T09:14:00Z", "source_system": "core_banking",
     "payload": {"txn_id": 50002, "amount": 148500.0, "direction": "credit",
                 "category": "salary_credit", "payment_ref": "TATA CONSULTANCY",
                 "merchant_city": "Mumbai", "txn_date": "2024-08-01",
                 "balance_after": 198200.0},
     "schema_version": "1.0"},
    {"event_id": "a1b2c3d4-0003", "customer_id": CUSTOMER, "event_type": "transaction",
     "event_timestamp": "2024-09-01T09:30:00Z", "source_system": "core_banking",
     "payload": {"txn_id": 50003, "amount": 181200.0, "direction": "credit",
                 "category": "salary_credit", "payment_ref": "INFOSYS LIMITED",
                 "merchant_city": "Mumbai", "txn_date": "2024-09-01",
                 "balance_after": 245100.0},
     "schema_version": "1.0"},
    {"event_id": "a1b2c3d4-0004", "customer_id": CUSTOMER, "event_type": "transaction",
     "event_timestamp": "2024-10-01T09:22:00Z", "source_system": "core_banking",
     "payload": {"txn_id": 50004, "amount": 181200.0, "direction": "credit",
                 "category": "salary_credit", "payment_ref": "INFOSYS LIMITED",
                 "merchant_city": "Bangalore", "txn_date": "2024-10-01",
                 "balance_after": 189300.0},
     "schema_version": "1.0"},
    {"event_id": "a1b2c3d4-0005", "customer_id": CUSTOMER, "event_type": "transaction",
     "event_timestamp": "2024-11-01T09:18:00Z", "source_system": "core_banking",
     "payload": {"txn_id": 50005, "amount": 181200.0, "direction": "credit",
                 "category": "salary_credit", "payment_ref": "INFOSYS LIMITED",
                 "merchant_city": "Bangalore", "txn_date": "2024-11-01",
                 "balance_after": 172800.0},
     "schema_version": "1.0"},
    # ---- pcop.transactions.v1 (location + lifecycle) ----
    {"event_id": "b2c3d4e5-0006", "customer_id": CUSTOMER, "event_type": "transaction",
     "event_timestamp": "2024-09-15T16:42:00Z", "source_system": "core_banking",
     "payload": {"txn_id": 50100, "amount": 85000.0, "direction": "debit",
                 "category": "transfer", "mcc_code": "6552",
                 "merchant_name": "PRESTIGE ESTATES", "merchant_city": "Bangalore",
                 "channel": "neft", "txn_date": "2024-09-15",
                 "balance_after": 160100.0, "is_international": False},
     "schema_version": "1.0"},
    {"event_id": "b2c3d4e5-0007", "customer_id": CUSTOMER, "event_type": "transaction",
     "event_timestamp": "2024-10-08T19:15:00Z", "source_system": "core_banking",
     "payload": {"txn_id": 50101, "amount": 4200.0, "direction": "debit",
                 "category": "retail", "mcc_code": "5712",
                 "merchant_name": "IKEA INDIA", "merchant_city": "Bangalore",
                 "channel": "card", "txn_date": "2024-10-08",
                 "balance_after": 185100.0},
     "schema_version": "1.0"},
    {"event_id": "b2c3d4e5-0008", "customer_id": CUSTOMER, "event_type": "transaction",
     "event_timestamp": "2024-10-12T20:45:00Z", "source_system": "core_banking",
     "payload": {"txn_id": 50102, "amount": 2800.0, "direction": "debit",
                 "category": "retail", "mcc_code": "5812",
                 "merchant_name": "ZOMATO BANGALORE", "merchant_city": "Bangalore",
                 "channel": "upi", "txn_date": "2024-10-12",
                 "balance_after": 182300.0},
     "schema_version": "1.0"},
    # Filler Mumbai history (May-Aug) so the 180d window establishes prior dominance
    *[
        {"event_id": f"mum-{i:04d}", "customer_id": CUSTOMER, "event_type": "transaction",
         "event_timestamp": f"2024-{month:02d}-{day:02d}T12:00:00Z",
         "source_system": "core_banking",
         "payload": {"txn_id": 49000 + i, "amount": 500 + i*10, "direction": "debit",
                     "category": "retail", "mcc_code": "5812",
                     "merchant_name": "MUMBAI RETAILER", "merchant_city": "Mumbai",
                     "channel": "upi", "txn_date": f"2024-{month:02d}-{day:02d}",
                     "balance_after": 180000 - i*100},
         "schema_version": "1.0"}
        for i, (month, day) in enumerate([
            (5, 5), (5, 12), (5, 19), (5, 26),
            (6, 3), (6, 10), (6, 17), (6, 24),
            (7, 8), (7, 15), (7, 22),
            (8, 5), (8, 12), (8, 19),
        ])
    ],
    # Filler Bangalore transactions in October to make new city >60% of recent 30d
    *[
        {"event_id": f"fill-{i:04d}", "customer_id": CUSTOMER, "event_type": "transaction",
         "event_timestamp": f"2024-10-{15+i:02d}T12:00:00Z", "source_system": "core_banking",
         "payload": {"txn_id": 50200 + i, "amount": 500 + i*10, "direction": "debit",
                     "category": "retail", "mcc_code": "5812",
                     "merchant_name": "LOCAL RETAILER", "merchant_city": "Bangalore",
                     "channel": "upi", "txn_date": f"2024-10-{15+i:02d}",
                     "balance_after": 180000 - i*100},
         "schema_version": "1.0"}
        for i in range(6)
    ],
    # ---- pcop.crm_notes.v1 ----
    {"event_id": "c3d4e5f6-0009", "customer_id": CUSTOMER, "event_type": "crm_note",
     "event_timestamp": "2024-08-20T11:30:00Z", "source_system": "crm",
     "payload": {"note_id": 9981, "note_type": "complaint",
                 "note_text": "Customer called to dispute processing fee charged on NEFT transfer. States fee was waived previously. Upset about inconsistency.",
                 "sentiment_score": -0.45, "issue_category": "fee_dispute",
                 "resolved": False, "channel": "call", "agent_id": "AG-204"},
     "schema_version": "1.0"},
    {"event_id": "c3d4e5f6-0010", "customer_id": CUSTOMER, "event_type": "crm_note",
     "event_timestamp": "2024-09-18T14:22:00Z", "source_system": "crm",
     "payload": {"note_id": 9995, "note_type": "enquiry",
                 "note_text": "Customer mentioned he has moved to Bangalore for a new role. Wants to update address. Asked about home loan pre-approval.",
                 "sentiment_score": 0.10, "issue_category": "product",
                 "resolved": True, "channel": "branch", "agent_id": "AG-118"},
     "schema_version": "1.0"},
    {"event_id": "c3d4e5f6-0011", "customer_id": CUSTOMER, "event_type": "crm_note",
     "event_timestamp": "2024-10-05T10:18:00Z", "source_system": "crm",
     "payload": {"note_id": 10042, "note_type": "complaint",
                 "note_text": "Customer called again regarding the unresolved August fee complaint. Mentioned he is considering switching to Kotak Mahindra.",
                 "sentiment_score": -0.72, "issue_category": "fee_dispute",
                 "resolved": False, "channel": "call", "agent_id": "AG-204"},
     "schema_version": "1.0"},
    # ---- pcop.app_events.v1 ----
    {"event_id": "d4e5f6g7-0012", "customer_id": CUSTOMER, "event_type": "app_event",
     "event_timestamp": "2024-08-15T08:12:00Z", "source_system": "mobile_app",
     "payload": {"event_type": "login", "feature_name": None,
                 "session_id": "S-77810", "session_duration_s": 340,
                 "platform": "ios", "app_version": "4.2.1"},
     "schema_version": "1.0"},
    {"event_id": "d4e5f6g7-0013", "customer_id": CUSTOMER, "event_type": "app_event",
     "event_timestamp": "2024-09-22T19:30:00Z", "source_system": "mobile_app",
     "payload": {"event_type": "login", "feature_name": None,
                 "session_id": "S-78201", "session_duration_s": 95,
                 "platform": "ios", "app_version": "4.2.1"},
     "schema_version": "1.0"},
    {"event_id": "d4e5f6g7-0014", "customer_id": CUSTOMER, "event_type": "app_event",
     "event_timestamp": "2024-10-25T21:15:00Z", "source_system": "mobile_app",
     "payload": {"event_type": "login", "feature_name": None,
                 "session_id": "S-78890", "session_duration_s": 42,
                 "platform": "ios", "app_version": "4.2.1"},
     "schema_version": "1.0"},
    # ---- pcop.complaints.v1 (Poisson count window) - prior months prime SPRT ----
    {"event_id": "e5f6g7h8-pri1", "customer_id": CUSTOMER,
     "event_type": "complaint_count_window",
     "event_timestamp": "2024-07-31T23:59:00Z", "source_system": "crm_aggregator",
     "payload": {"window": "monthly", "window_start": "2024-07-01",
                 "window_end": "2024-07-31", "complaint_count": 1,
                 "baseline_lambda_0": 0.3},
     "schema_version": "1.0"},
    {"event_id": "e5f6g7h8-pri2", "customer_id": CUSTOMER,
     "event_type": "complaint_count_window",
     "event_timestamp": "2024-08-31T23:59:00Z", "source_system": "crm_aggregator",
     "payload": {"window": "monthly", "window_start": "2024-08-01",
                 "window_end": "2024-08-31", "complaint_count": 1,
                 "baseline_lambda_0": 0.3},
     "schema_version": "1.0"},
    {"event_id": "e5f6g7h8-pri3", "customer_id": CUSTOMER,
     "event_type": "complaint_count_window",
     "event_timestamp": "2024-09-30T23:59:00Z", "source_system": "crm_aggregator",
     "payload": {"window": "monthly", "window_start": "2024-09-01",
                 "window_end": "2024-09-30", "complaint_count": 1,
                 "baseline_lambda_0": 0.3},
     "schema_version": "1.0"},
    {"event_id": "e5f6g7h8-0015", "customer_id": CUSTOMER,
     "event_type": "complaint_count_window",
     "event_timestamp": "2024-10-31T23:59:00Z", "source_system": "crm_aggregator",
     "payload": {"window": "monthly", "window_start": "2024-10-01",
                 "window_end": "2024-10-31", "complaint_count": 6,
                 "baseline_lambda_0": 0.3},
     "schema_version": "1.0"},
]


def route_event(event: CanonicalEvent, agents: dict, sink: ListSink) -> None:
    """Per-topic dispatch matching services.detection.main.TOPIC_TO_AGENT_TYPES."""
    payload = event.payload
    et = event.event_type

    if et == "transaction":
        if payload.get("category") == "salary_credit":
            agents["salary"].handle(event)
        # All transactions feed location, transaction_freq accumulator,
        # stress (overdraft + MCC), and lifecycle.
        agents["location"].handle(event)
        agents["transaction_freq"].handle(event)
        agents["stress"].handle(event)
        agents["lifecycle"].handle(event)
    elif et == "crm_note":
        agents["complaint_sentiment"].handle(event)
    elif et == "app_event":
        agents["engagement"].handle(event)
        agents["feature_usage"].handle(event)
    elif et == "complaint_count_window":
        agents["complaint_volume"].handle(event)
    elif et == "account_event":
        agents["lifecycle"].handle(event)


def main():
    state_store = InMemoryStateStore()
    baselines = DictBaselineProvider(BASELINES)
    sink = ListSink()

    agents = {
        "salary":              SalaryAgent(state_store, baselines, sink, publish_only_alarms=True),
        "location":            LocationAgent(state_store, baselines, sink, publish_only_alarms=True),
        "complaint_sentiment": ComplaintSentimentAgent(state_store, baselines, sink, publish_only_alarms=True),
        "complaint_volume":    ComplaintVolumeAgent(state_store, baselines, sink, publish_only_alarms=True),
        "engagement":          EngagementAgent(state_store, baselines, sink, publish_only_alarms=True),
        "transaction_freq":    TransactionDriftAgent(state_store, baselines, sink, publish_only_alarms=True),
        "stress":              StressAgent(state_store, baselines, sink, publish_only_alarms=True),
        "lifecycle":           LifecycleAgent(state_store, baselines, sink, publish_only_alarms=True),
        "feature_usage":       FeatureUsageAgent(state_store, baselines, sink, publish_only_alarms=True),
    }
    joint = BocpdJointDetector(state_store, baselines, sink, publish_only_alarms=True)

    # Sort events chronologically and dispatch
    sorted_events = sorted(EVENTS, key=lambda e: e["event_timestamp"])
    for raw in sorted_events:
        event = CanonicalEvent.model_validate(raw)
        route_event(event, agents, sink)

    # After all events flow, run the BOCPD joint detector with recent sub-threshold signals.
    # For demo: feed it the latest "non-alarm" CUSUM ratios as if we'd pulled them from DB.
    # In production we'd pull recent_signal_results from PostgreSQL.
    simulated_subthreshold = [
        _fake_subthreshold("transaction_freq", 0.62),
        _fake_subthreshold("engagement", 0.71),
        _fake_subthreshold("complaint_sentiment", 0.58),
    ]
    joint_alarm = joint.evaluate_customer(
        CUSTOMER, simulated_subthreshold,
        now=datetime(2024, 11, 1, 9, 20, tzinfo=timezone.utc),
    )
    if joint_alarm:
        sink.alarms.append(joint_alarm)

    # ---- Print results in the same shape the spec lists ----
    print("\n" + "=" * 70)
    print(f"LAYER 2 OUTPUTS for {CUSTOMER}: {len(sink.alarms)} signal results emitted")
    print("=" * 70)
    for sig in sink.alarms:
        alarm = signal_result_to_alarm(sig)
        print(f"\n--- {sig.signal_type.upper()} [{sig.method_used}] ---")
        print(json.dumps(alarm.model_dump(mode="json"), indent=2, default=str))

    return sink.alarms


def _fake_subthreshold(signal_type: str, ratio: float):
    """Construct a SignalResult shell with the ratio embedded as cusum_value/threshold."""
    from .common.schemas import SignalResult
    return SignalResult(
        customer_id=CUSTOMER,
        signal_type=signal_type,
        detected=False,
        confidence=0.0,
        evidence=[],
        raw_data={},
        cusum_value=ratio,         # ratio expressed as value
        alarm_threshold=1.0,       # so cusum/threshold == ratio
        method_used="cusum",
        evaluated_at=datetime(2024, 11, 1, tzinfo=timezone.utc),
    )


if __name__ == "__main__":
    main()
