"""
SPRT — Sequential Probability Ratio Test for Poisson count streams.

For each new observation x_t (a count over a fixed window):
    increment = x_t * log(lambda_1 / lambda_0) - (lambda_1 - lambda_0)
    Lambda_t  = Lambda_{t-1} + increment

Decision bounds:
    Upper B  = log((1 - beta) / alpha)        => accept H1 (alarm)
    Lower A  = log(beta / (1 - alpha))        => accept H0 (in control)
"""
import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class SprtState:
    lambda_t: float = 0.0


@dataclass
class SprtResult:
    lambda_t: float
    upper_bound: float
    lower_bound: float
    decision: str          # 'H1_accepted' | 'H0_accepted' | 'continue'
    alarm: bool
    confidence: float


class SprtPoisson:
    def __init__(self, lambda_0: float, lambda_1: float, alpha: float = 0.01, beta: float = 0.10):
        if lambda_0 <= 0 or lambda_1 <= 0:
            raise ValueError("lambdas must be positive")
        if not (0 < alpha < 1) or not (0 < beta < 1):
            raise ValueError("alpha and beta must be in (0, 1)")
        self.lambda_0 = lambda_0
        self.lambda_1 = lambda_1
        self.alpha = alpha
        self.beta = beta
        self.B = math.log((1.0 - beta) / alpha)
        self.A = math.log(beta / (1.0 - alpha))
        self._log_ratio = math.log(lambda_1 / lambda_0)
        self._diff = lambda_1 - lambda_0

    def update(self, x: float, state: SprtState, reset_on_decision: bool = True) -> SprtResult:
        inc = x * self._log_ratio - self._diff
        lam_t = state.lambda_t + inc

        if lam_t >= self.B:
            decision, alarm = "H1_accepted", True
            confidence = min((lam_t - self.A) / (self.B - self.A), 1.0)
        elif lam_t <= self.A:
            decision, alarm = "H0_accepted", False
            confidence = 0.0
        else:
            decision, alarm = "continue", False
            confidence = max(0.0, (lam_t - self.A) / (self.B - self.A))

        # After a terminal decision the canonical SPRT resets the statistic.
        if reset_on_decision and decision in ("H1_accepted", "H0_accepted"):
            lam_t = 0.0

        return SprtResult(
            lambda_t=lam_t,
            upper_bound=self.B,
            lower_bound=self.A,
            decision=decision,
            alarm=alarm,
            confidence=confidence,
        )
