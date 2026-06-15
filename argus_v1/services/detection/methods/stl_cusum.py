"""
STL + CUSUM on residuals.

Pipeline for seasonal signals (e.g. daily transaction counts):
    1. Decompose Y_t = T_t + S_t + R_t via STL with 7-day seasonal period.
    2. Apply standard CUSUM to R_t.

This wraps statsmodels.tsa.seasonal.STL for the decomposition and reuses
the streaming CUSUM. For streaming use we re-fit STL on the trailing
window (default 60 days) each time and feed the latest residual to CUSUM.
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from .cusum import Cusum, CusumResult, CusumState

try:
    from statsmodels.tsa.seasonal import STL
    _HAS_STATSMODELS = True
except ImportError:
    _HAS_STATSMODELS = False


@dataclass
class StlCusumResult:
    residual: float
    cusum: CusumResult
    trend_value: float
    seasonal_value: float


class StlCusum:
    """Stateless wrapper: caller supplies the rolling window each call."""

    def __init__(self, mu_0: float, sigma: float, period: int = 7,
                 k_sigma: float = 0.5, H_sigma: float = 4.0):
        if not _HAS_STATSMODELS:
            raise RuntimeError("statsmodels required for STL")
        self.period = period
        self.cusum = Cusum(mu_0=mu_0, sigma=sigma, k_sigma=k_sigma, H_sigma=H_sigma)

    def step(self, series: pd.Series, state: CusumState) -> StlCusumResult:
        """
        Args:
            series: pd.Series indexed by date with the latest observation last.
                    Should be at least 2 * period long.
            state:  current CUSUM state (mutated in place by caller).
        Returns:
            StlCusumResult for the LATEST point of the series.
        """
        if len(series) < 2 * self.period:
            raise ValueError(f"Need at least {2*self.period} obs for STL")
        stl = STL(series, period=self.period, robust=True).fit()
        latest_residual = float(stl.resid.iloc[-1])
        trend = float(stl.trend.iloc[-1])
        seasonal = float(stl.seasonal.iloc[-1])

        cusum_result = self.cusum.update(latest_residual, state)
        state.s_plus = cusum_result.s_plus
        state.s_minus = cusum_result.s_minus

        return StlCusumResult(residual=latest_residual, cusum=cusum_result,
                              trend_value=trend, seasonal_value=seasonal)
