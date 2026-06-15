"""
BOCPD — Bayesian Online Changepoint Detection (Adams & MacKay, 2007).

Maintains a posterior distribution over the run length r_t (number of time-steps
since the last changepoint), updated each step with:

    P(r_t | x_1:t) proportional_to  predictive(x_t | r_t, history)
                                    * hazard-based transition

Underlying model: Normal-InverseGamma conjugate prior (univariate Gaussian
with unknown mean and variance). Closed-form predictive = Student-t.

This implementation is multivariate-extensible by feeding a joint score
(e.g. weighted average of co-active CUSUM ratios). It is used as the
JOINT ARBITER across signals, not on raw event streams.
"""
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class BocpdState:
    # Run-length posterior over r_t in {0, 1, ..., t}
    run_length_probs: list[float] = field(default_factory=lambda: [1.0])
    # Sufficient stats per run-length hypothesis (Normal-InverseGamma)
    mu: list[float] = field(default_factory=list)         # posterior mean
    kappa: list[float] = field(default_factory=list)      # mean precision
    alpha: list[float] = field(default_factory=list)      # IG shape
    beta: list[float] = field(default_factory=list)       # IG scale
    t: int = 0


@dataclass
class BocpdResult:
    changepoint_probability: float   # P(r_t = 0 | x_1:t)
    most_likely_run_length: int
    alarm: bool
    threshold: float


class Bocpd:
    """
    Constant hazard BOCPD with Normal-InverseGamma predictive.

    Args:
        hazard: constant hazard (1/expected-run-length). 1/200 ~ retail-banking default.
        alarm_prob: P(r_t = 0) above which to declare a changepoint.
        prior_mu, prior_kappa, prior_alpha, prior_beta: NIG hyperparameters.
    """

    def __init__(self, hazard: float = 1.0 / 200.0, alarm_prob: float = 0.60,
                 prior_mu: float = 0.0, prior_kappa: float = 1.0,
                 prior_alpha: float = 1.0, prior_beta: float = 1.0,
                 max_run_length: int = 500):
        self.hazard = hazard
        self.alarm_prob = alarm_prob
        self.mu0 = prior_mu
        self.kappa0 = prior_kappa
        self.alpha0 = prior_alpha
        self.beta0 = prior_beta
        self.max_run_length = max_run_length

    def _student_t_pdf(self, x: float, mu: float, kappa: float,
                       alpha: float, beta: float) -> float:
        # Predictive: x ~ t_{2*alpha}(mu, beta*(kappa+1)/(alpha*kappa))
        df = 2.0 * alpha
        scale_sq = beta * (kappa + 1.0) / (alpha * kappa)
        scale = math.sqrt(max(scale_sq, 1e-12))
        z = (x - mu) / scale
        log_norm = (math.lgamma((df + 1) / 2) - math.lgamma(df / 2)
                    - 0.5 * math.log(df * math.pi) - math.log(scale))
        log_pdf = log_norm - 0.5 * (df + 1) * math.log1p(z * z / df)
        return math.exp(log_pdf)

    def init_state(self) -> BocpdState:
        return BocpdState(
            run_length_probs=[1.0],
            mu=[self.mu0],
            kappa=[self.kappa0],
            alpha=[self.alpha0],
            beta=[self.beta0],
            t=0,
        )

    def update(self, x: float, state: BocpdState) -> BocpdResult:
        # Capture pre-update mode (longest-running hypothesis) so we can
        # detect when the run-length posterior "collapses" to a new regime.
        pre_max_prob = max(state.run_length_probs) if state.run_length_probs else 0.0
        pre_mode_rl = (state.run_length_probs.index(pre_max_prob)
                       if state.run_length_probs else 0)

        # 1. Predictive probabilities under each run-length hypothesis
        preds = np.array([
            self._student_t_pdf(x, state.mu[i], state.kappa[i],
                                state.alpha[i], state.beta[i])
            for i in range(len(state.mu))
        ])

        probs = np.array(state.run_length_probs)

        # 2. Growth probabilities: run-length increments by 1
        growth = probs * preds * (1.0 - self.hazard)
        # 3. Changepoint probability: r_t resets to 0
        cp_prob = float((probs * preds * self.hazard).sum())

        # New posterior (unnormalised)
        new_probs = np.concatenate([[cp_prob], growth])
        total = new_probs.sum()
        if total > 0:
            new_probs = new_probs / total
        else:
            new_probs = np.zeros_like(new_probs)
            new_probs[0] = 1.0

        # 4. Posterior sufficient-stat update for each hypothesis
        new_mu = [self.mu0] + [
            (state.kappa[i] * state.mu[i] + x) / (state.kappa[i] + 1.0)
            for i in range(len(state.mu))
        ]
        new_kappa = [self.kappa0] + [state.kappa[i] + 1.0 for i in range(len(state.mu))]
        new_alpha = [self.alpha0] + [state.alpha[i] + 0.5 for i in range(len(state.mu))]
        new_beta = [self.beta0] + [
            state.beta[i] + (state.kappa[i] * (x - state.mu[i]) ** 2)
            / (2.0 * (state.kappa[i] + 1.0))
            for i in range(len(state.mu))
        ]

        # 5. Truncate to max_run_length for memory bounds
        if len(new_probs) > self.max_run_length:
            new_probs = new_probs[: self.max_run_length]
            new_mu = new_mu[: self.max_run_length]
            new_kappa = new_kappa[: self.max_run_length]
            new_alpha = new_alpha[: self.max_run_length]
            new_beta = new_beta[: self.max_run_length]
            s = new_probs.sum()
            if s > 0:
                new_probs = new_probs / s

        state.run_length_probs = new_probs.tolist()
        state.mu = new_mu
        state.kappa = new_kappa
        state.alpha = new_alpha
        state.beta = new_beta
        state.t += 1

        # ---- Alarm condition ----
        # Classic BOCPD uses P(r_t = 0) but that is dominated by the
        # hazard constant; the practical alarm is run-length collapse:
        # the previously dominant hypothesis abruptly loses its mass.
        most_likely_rl = int(np.argmax(new_probs))
        post_max_prob = float(new_probs[most_likely_rl])

        # Confidence: how much probability collapsed away from the
        # established regime to short run-lengths after this observation.
        short_rl_mass = float(np.sum(new_probs[:max(1, len(new_probs) // 4)]))
        regime_collapse = max(0.0, pre_max_prob - post_max_prob)

        # Combine: alarm fires when either the established regime lost
        # > 0.30 probability mass OR most run-length mass sits in r <= t/4.
        alarm = regime_collapse > 0.30 or (
            short_rl_mass > self.alarm_prob and most_likely_rl < max(5, state.t // 4)
        )

        # Reported "changepoint probability" is now the run-length collapse
        # magnitude clipped to [0,1] (closer to what dashboards actually want).
        cp_posterior = min(1.0, regime_collapse + short_rl_mass)

        return BocpdResult(
            changepoint_probability=cp_posterior,
            most_likely_run_length=most_likely_rl,
            alarm=alarm,
            threshold=self.alarm_prob,
        )
