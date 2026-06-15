"""Abstract base class for HERALD per-stream signal agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class SignalResult:
    """Standardised output from any HERALD agent."""

    signal_type: str
    detected: bool
    confidence: float          # [0.0, 1.0]
    p_value: float             # raw p-value (fed to WARDEN)
    evidence: list[str]
    method_used: str
    statistic: float           # primary test statistic value
    threshold: float           # alarm threshold
    direction: str             # "increase" | "decrease" | "none"
    baseline_mean: float
    baseline_std: float
    onset_estimate: date | None = None
    method_version: str = "argus-v1"


class BaseHeraldAgent(ABC):
    """Base class for all HERALD stream agents."""

    signal_type: str = ""
    method_used: str = ""

    @abstractmethod
    def evaluate(self, customer_id: str, data: dict[str, Any]) -> SignalResult:
        """Evaluate the signal stream and return a SignalResult.

        Args:
            customer_id: Unique customer identifier.
            data: Signal-specific data dictionary (varies by agent).

        Returns:
            SignalResult with detection outcome and evidence.
        """
        ...
