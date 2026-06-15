"""
EWMA — Exponentially Weighted Moving Average control chart.

    Z_t   = lambda * x_t + (1 - lambda) * Z_{t-1}
    sigma_Z_t = sigma * sqrt( (lambda/(2-lambda)) * (1 - (1-lambda)^(2t)) )
    UCL/LCL = mu_0 +/- L * sigma_Z_t

Default params: lambda = 0.3, L = 3.
"""
import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class EwmaState:
    z_prev: float          # initialised to mu_0 on first call
    t: int = 0             # number of observations seen


@dataclass
class EwmaResult:
    z_t: float
    UCL: float
    LCL: float
    alarm: bool
    direction: Optional[str]
    confidence: float


class Ewma:
    def __init__(self, mu_0: float, sigma: float, lam: float = 0.3, L: float = 3.0):
        if not (0.0 < lam <= 1.0):
            raise ValueError("lambda must be in (0, 1]")
        self.mu_0 = mu_0
        self.sigma = sigma
        self.lam = lam
        self.L = L

    def update(self, x: float, state: EwmaState) -> EwmaResult:
        t = state.t + 1
        z_t = self.lam * x + (1.0 - self.lam) * state.z_prev

        time_factor = 1.0 - (1.0 - self.lam) ** (2 * t)
        sigma_z = self.sigma * math.sqrt((self.lam / (2.0 - self.lam)) * time_factor)
        UCL = self.mu_0 + self.L * sigma_z
        LCL = self.mu_0 - self.L * sigma_z

        if z_t > UCL:
            alarm, direction = True, "up"
        elif z_t < LCL:
            alarm, direction = True, "down"
        else:
            alarm, direction = False, None

        # confidence = signed normalised deviation from the nearest limit
        if alarm:
            ref = UCL if direction == "up" else LCL
            denom = max(abs(ref - self.mu_0), 1e-9)
            confidence = min(abs(z_t - ref) / denom + 0.5, 1.0)
        else:
            confidence = 0.0

        return EwmaResult(z_t=z_t, UCL=UCL, LCL=LCL, alarm=alarm,
                          direction=direction, confidence=confidence)
