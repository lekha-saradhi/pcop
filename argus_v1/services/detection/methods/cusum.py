"""
CUSUM — Cumulative Sum Control Chart (two-sided).

Optimal for detecting sustained mean shifts in approximately Gaussian streams.
    S+_t = max(0, S+_{t-1} + (x_t - mu_0) - k)
    S-_t = max(0, S-_{t-1} - (x_t - mu_0) - k)
    Alarm: S+_t > H  or  S-_t > H

Default params: k = 0.5 * sigma, H = 4 * sigma (target ARL0 ~ 500).
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class CusumState:
    s_plus: float = 0.0
    s_minus: float = 0.0


@dataclass
class CusumResult:
    s_plus: float
    s_minus: float
    alarm: bool
    direction: Optional[str]  # 'up' | 'down' | None
    threshold: float
    statistic_value: float    # max(s_plus, s_minus) for reporting
    confidence: float         # bounded ratio of statistic to threshold


class Cusum:
    def __init__(self, mu_0: float, sigma: float, k_sigma: float = 0.5, H_sigma: float = 4.0):
        if sigma <= 0:
            raise ValueError("sigma must be positive")
        self.mu_0 = mu_0
        self.sigma = sigma
        self.k = k_sigma * sigma          # slack / allowance
        self.H = H_sigma * sigma          # alarm threshold

    def update(self, x: float, state: CusumState) -> CusumResult:
        s_plus = max(0.0, state.s_plus + (x - self.mu_0) - self.k)
        s_minus = max(0.0, state.s_minus - (x - self.mu_0) - self.k)

        alarm = (s_plus > self.H) or (s_minus > self.H)
        if alarm:
            direction = "up" if s_plus > s_minus else "down"
        else:
            direction = None

        stat = max(s_plus, s_minus)
        confidence = min(stat / self.H, 1.0) if self.H > 0 else 0.0

        return CusumResult(
            s_plus=s_plus,
            s_minus=s_minus,
            alarm=alarm,
            direction=direction,
            threshold=self.H,
            statistic_value=stat,
            confidence=confidence,
        )
