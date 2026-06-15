"""MCC temporal cluster scorer for lifecycle event detection.

Cluster scoring replaces single-MCC whitelist triggers to reduce
false positives from isolated incidental transactions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LifecycleEvent(str, Enum):
    MARRIAGE = "marriage"
    NEW_BABY = "new_baby"
    HOME_PURCHASE = "home_purchase"
    BEREAVEMENT = "bereavement"
    NONE = "none"


# MCC cluster definitions: required MCCs + supporting MCCs + thresholds
_CLUSTER_CONFIGS: dict[LifecycleEvent, dict] = {
    LifecycleEvent.MARRIAGE: {
        "required": {5944, 7011},    # jewellery, hotels/lodging
        "supporting": {5947, 7296, 5641},  # gifts, clothing rental, children's
        "base_score": 0.50,
        "support_increment": 0.20,
        "threshold": 0.70,
    },
    LifecycleEvent.NEW_BABY: {
        "required": {5641, 5999},    # children's clothing, baby products
        "supporting": {8099, 8111},  # paediatric, legal/will
        "base_score": 0.50,
        "support_increment": 0.25,
        "threshold": 0.75,
    },
    LifecycleEvent.HOME_PURCHASE: {
        "required": {6552, 7389},    # real estate, conveyancing
        "supporting": {5211, 5712},  # lumber/hardware, furniture
        "base_score": 0.60,
        "support_increment": 0.20,
        "threshold": 0.80,
    },
    LifecycleEvent.BEREAVEMENT: {
        "required": {7261},          # funeral services
        "supporting": {8111, 5912},  # legal services, pharmacies
        "base_score": 0.70,
        "support_increment": 0.15,
        "threshold": 0.70,
    },
}


@dataclass
class MCCClusterResult:
    detected: bool
    event: LifecycleEvent
    score: float
    contributing_mccs: list[int]
    confidence: float
    evidence: list[str]


def score_mcc_cluster(mccs_30d: set[int]) -> MCCClusterResult:
    """Score MCC set against all lifecycle event clusters.

    mccs_30d: set of unique MCC codes seen in the past 30 days.
    Returns the highest-confidence detected event.
    """
    best: MCCClusterResult | None = None

    for event, cfg in _CLUSTER_CONFIGS.items():
        required: set[int] = cfg["required"]
        supporting: set[int] = cfg["supporting"]

        hit_required = required & mccs_30d
        hit_supporting = supporting & mccs_30d

        if not hit_required:
            continue

        score = cfg["base_score"] + len(hit_supporting) * cfg["support_increment"]
        score = min(score, 1.0)
        contributing = sorted(hit_required | hit_supporting)
        evidence = [
            f"Required MCC {m} present" for m in sorted(hit_required)
        ] + [
            f"Supporting MCC {m} present" for m in sorted(hit_supporting)
        ]

        result = MCCClusterResult(
            detected=score >= cfg["threshold"],
            event=event,
            score=score,
            contributing_mccs=contributing,
            confidence=score,
            evidence=evidence,
        )

        if best is None or score > best.score:
            best = result

    if best is None or not best.detected:
        return MCCClusterResult(
            detected=False,
            event=LifecycleEvent.NONE,
            score=0.0,
            contributing_mccs=[],
            confidence=0.0,
            evidence=[],
        )
    return best
