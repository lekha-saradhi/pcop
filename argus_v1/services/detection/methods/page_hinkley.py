"""
Page-Hinkley Test — lightweight CUSUM variant for high-throughput count streams.

    m_t = x_t - x_bar_t - delta
    M_t = M_{t-1} + m_t
    T_t = M_t - min_{1<=i<=t}(M_i)
    Alarm: T_t > lambda
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class PageHinkleyState:
    n: int = 0
    running_mean: float = 0.0
    M_t: float = 0.0
    M_min: float = 0.0


@dataclass
class PageHinkleyResult:
    T_t: float
    threshold: float
    alarm: bool
    running_mean: float
    confidence: float


class PageHinkley:
    def __init__(self, delta: float = 0.01, threshold: float = 50.0):
        self.delta = delta
        self.threshold = threshold

    def update(self, x: float, state: PageHinkleyState) -> PageHinkleyResult:
        n = state.n + 1
        running_mean = state.running_mean + (x - state.running_mean) / n

        m_t = x - running_mean - self.delta
        M_t = state.M_t + m_t
        M_min = min(state.M_min, M_t)

        T_t = M_t - M_min
        alarm = T_t > self.threshold
        confidence = min(T_t / self.threshold, 1.0) if self.threshold > 0 else 0.0

        # Mutate state into the returned object via the caller; we just compute.
        state.n = n
        state.running_mean = running_mean
        state.M_t = M_t
        state.M_min = M_min

        return PageHinkleyResult(T_t=T_t, threshold=self.threshold, alarm=alarm,
                                 running_mean=running_mean, confidence=confidence)
