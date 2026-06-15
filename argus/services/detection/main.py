"""ARGUS Engine — Main evaluation pipeline (Layer 2).

Orchestrates HERALD agents → NEXUS → ORACLE → WARDEN → ECHO for each
customer evaluation. Designed for event-driven, real-time invocation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Optional

from services.detection.agents.base_agent import SignalResult
from services.detection.agents.herald_engagement import HeraldEngagementAgent
from services.detection.agents.herald_lifecycle import HeraldLifecycleAgent
from services.detection.agents.herald_location import HeraldLocationAgent
from services.detection.agents.herald_market import HeraldMarketAgent
from services.detection.agents.herald_recency import HeraldRecencyAgent
from services.detection.agents.herald_salary import HeraldSalaryAgent
from services.detection.agents.herald_sentiment import HeraldSentimentAgent
from services.detection.agents.herald_stress import HeraldStressAgent
from services.detection.agents.herald_transaction import HeraldTransactionAgent
from services.detection.joint.nexus import NEXUSResult, NEXUSState, nexus_evaluate
from services.detection.joint.oracle import ORACLEResult, oracle_evaluate
from services.detection.joint.warden import WARDENResult, warden_evaluate
from services.detection.state.echo import AlarmPayload, ECHOPublisher, build_alarm_payload

logger = logging.getLogger(__name__)

# Registry of all HERALD agents
_HERALD_AGENTS = [
    HeraldTransactionAgent(),
    HeraldRecencyAgent(),
    HeraldSalaryAgent(),
    HeraldSentimentAgent(),
    HeraldEngagementAgent(),
    HeraldStressAgent(),
    HeraldLocationAgent(),
    HeraldLifecycleAgent(),
    HeraldMarketAgent(),
]


@dataclass
class ARGUSInput:
    """All data needed to evaluate one customer in one ARGUS run."""

    customer_id: str
    today: date
    # Per-agent data dictionaries (keyed by signal_type)
    herald_data: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Joint detector inputs
    signal_matrix: Any = None         # np.ndarray (n_days, 8) for NEXUS + ORACLE
    signal_dates: list[date] = field(default_factory=list)
    baseline_mus: Any = None           # np.ndarray (8,) for ORACLE
    baseline_sigmas: Any = None        # np.ndarray (8,)
    nexus_state: NEXUSState | None = None


@dataclass
class ARGUSOutput:
    """Comprehensive output for one customer evaluation."""

    customer_id: str
    evaluated_at: str
    warden: WARDENResult
    nexus: NEXUSResult
    oracle: ORACLEResult
    herald_results: dict[str, SignalResult]
    alarm_payload: AlarmPayload | None


class ARGUSEngine:
    """Stateless evaluation engine — caller manages state persistence."""

    def __init__(self, publisher: ECHOPublisher | None = None) -> None:
        self._publisher = publisher

    def evaluate(self, inp: ARGUSInput) -> ARGUSOutput:
        """Run full ARGUS pipeline for one customer.

        Args:
            inp: ARGUSInput with all agent data and joint detector inputs.

        Returns:
            ARGUSOutput with WARDEN decision, NEXUS/ORACLE results, ECHO payload.
        """
        now = datetime.now(tz=timezone.utc)

        # --- 1. HERALD: run all per-stream agents ---
        herald_results: dict[str, SignalResult] = {}
        p_values: dict[str, float] = {}

        for agent in _HERALD_AGENTS:
            agent_data = inp.herald_data.get(agent.signal_type)
            if agent_data is None:
                continue
            try:
                agent_data["today"] = inp.today
                result = agent.evaluate(inp.customer_id, agent_data)
                herald_results[agent.signal_type] = result
                p_values[agent.signal_type] = result.p_value
            except Exception as exc:
                logger.error(
                    "ARGUS: HERALD agent %s failed for %s: %s",
                    agent.signal_type, inp.customer_id, exc,
                )

        # --- 2. NEXUS: correlation structure monitor ---
        nexus_result = NEXUSResult(
            nexus_detected=False, lrt_p_value=1.0, frobenius_delta=0.0,
            changed_edges=[], confidence=0.0, evidence=[],
        )
        if inp.nexus_state is not None and inp.signal_matrix is not None:
            nexus_result = nexus_evaluate(inp.nexus_state, inp.signal_matrix)
            p_values["nexus_correlation"] = nexus_result.lrt_p_value

        # --- 3. ORACLE: multiscale changepoint detector ---
        oracle_result = ORACLEResult(
            oracle_detected=False, alarm_scale=None, alarm_dimensions=[],
            test_statistic=0.0, threshold=0.0, onset_estimate=None,
            p_value=1.0, evidence=[],
        )
        if inp.signal_matrix is not None and len(inp.signal_dates) > 0:
            oracle_result = oracle_evaluate(
                inp.signal_matrix, inp.signal_dates,
                mus=inp.baseline_mus, sigmas=inp.baseline_sigmas,
            )
            p_values["oracle_multivariate"] = oracle_result.p_value

        # --- 4. WARDEN: BH-FDR multiple testing control ---
        warden_result = warden_evaluate(
            p_values,
            oracle_detected=oracle_result.oracle_detected,
            nexus_detected=nexus_result.nexus_detected,
        )

        # --- 5. ECHO: build and publish alarm payload ---
        payload: AlarmPayload | None = None
        if warden_result.alarm:
            signal_details: dict[str, Any] = {}
            for name, res in herald_results.items():
                if name in warden_result.rejected_tests:
                    signal_details[name] = {
                        "method": res.method_used,
                        "statistic": res.statistic,
                        "threshold": res.threshold,
                        "direction": res.direction,
                        "onset_estimate": res.onset_estimate.isoformat() if res.onset_estimate else None,
                        "evidence": res.evidence,
                    }

            active_count = sum(1 for r in herald_results.values() if r.detected)

            payload = build_alarm_payload(
                customer_id=inp.customer_id,
                severity=warden_result.severity,
                rejected_tests=warden_result.rejected_tests,
                adjusted_p=warden_result.fdr_adjusted_p_values,
                signal_details=signal_details,
                nexus_changed=nexus_result.nexus_detected,
                oracle_onset=oracle_result.onset_estimate,
                active_signal_count=active_count,
                now=now,
            )

            if self._publisher is not None:
                self._publisher.publish(payload)

            logger.info(
                "ARGUS alarm: customer=%s severity=%s tests=%s",
                inp.customer_id, warden_result.severity, warden_result.rejected_tests,
            )

        return ARGUSOutput(
            customer_id=inp.customer_id,
            evaluated_at=now.isoformat(),
            warden=warden_result,
            nexus=nexus_result,
            oracle=oracle_result,
            herald_results=herald_results,
            alarm_payload=payload,
        )
