"""
Unit tests for statistical methods. Run with:
    PYTHONPATH=. python -m unittest services/detection/tests/test_methods.py
"""
import unittest

from services.detection.methods import (
    Cusum, CusumState, Ewma, EwmaState,
    SprtPoisson, SprtState, PageHinkley, PageHinkleyState,
    Bocpd,
)


class TestCusum(unittest.TestCase):
    def test_stays_quiet_on_in_control(self):
        c = Cusum(mu_0=100.0, sigma=10.0, k_sigma=0.5, H_sigma=4.0)
        s = CusumState()
        for x in [99, 101, 100, 102, 98, 100, 99, 101]:
            r = c.update(x, s)
            s.s_plus, s.s_minus = r.s_plus, r.s_minus
            self.assertFalse(r.alarm)

    def test_detects_sustained_upward_shift(self):
        c = Cusum(mu_0=100.0, sigma=10.0, k_sigma=0.5, H_sigma=4.0)
        s = CusumState()
        fired = False
        for x in [115, 117, 116, 118, 116, 117, 120, 119]:
            r = c.update(x, s)
            s.s_plus, s.s_minus = r.s_plus, r.s_minus
            if r.alarm:
                fired = True
                self.assertEqual(r.direction, "up")
                break
        self.assertTrue(fired)

    def test_detects_sustained_downward_shift(self):
        c = Cusum(mu_0=100.0, sigma=10.0, k_sigma=0.5, H_sigma=4.0)
        s = CusumState()
        fired = False
        for x in [85, 83, 84, 82, 84, 83, 80, 81]:
            r = c.update(x, s)
            s.s_plus, s.s_minus = r.s_plus, r.s_minus
            if r.alarm:
                fired = True
                self.assertEqual(r.direction, "down")
                break
        self.assertTrue(fired)

    def test_confidence_in_range(self):
        c = Cusum(mu_0=0.0, sigma=1.0)
        s = CusumState()
        r = c.update(10.0, s)
        self.assertGreaterEqual(r.confidence, 0.0)
        self.assertLessEqual(r.confidence, 1.0)


class TestEwma(unittest.TestCase):
    def test_stays_quiet_on_in_control(self):
        e = Ewma(mu_0=0.5, sigma=0.05, lam=0.3, L=3.0)
        s = EwmaState(z_prev=0.5, t=0)
        for x in [0.49, 0.51, 0.50, 0.52, 0.49, 0.50]:
            r = e.update(x, s)
            s.z_prev, s.t = r.z_t, s.t + 1
            self.assertFalse(r.alarm)

    def test_detects_downward_drift(self):
        e = Ewma(mu_0=0.5, sigma=0.05, lam=0.3, L=3.0)
        s = EwmaState(z_prev=0.5, t=0)
        fired = False
        for x in [0.30, 0.25, 0.20, 0.15, 0.10]:
            r = e.update(x, s)
            s.z_prev, s.t = r.z_t, s.t + 1
            if r.alarm:
                fired = True
                self.assertEqual(r.direction, "down")
                break
        self.assertTrue(fired)


class TestSprt(unittest.TestCase):
    def test_accepts_h1_on_elevated_count(self):
        sprt = SprtPoisson(lambda_0=0.3, lambda_1=0.6, alpha=0.01, beta=0.10)
        s = SprtState()
        fired = False
        for x in [2, 2, 2, 2, 2]:
            r = sprt.update(x, s, reset_on_decision=False)
            s.lambda_t = r.lambda_t
            if r.alarm:
                fired = True
                self.assertEqual(r.decision, "H1_accepted")
                break
        self.assertTrue(fired)

    def test_continues_on_neutral_data(self):
        sprt = SprtPoisson(lambda_0=0.3, lambda_1=0.6, alpha=0.01, beta=0.10)
        s = SprtState()
        for x in [0, 1, 0, 1]:
            r = sprt.update(x, s, reset_on_decision=False)
            s.lambda_t = r.lambda_t
            self.assertFalse(r.alarm)


class TestPageHinkley(unittest.TestCase):
    def test_detects_distribution_shift(self):
        ph = PageHinkley(delta=0.005, threshold=3.0)
        s = PageHinkleyState()
        # In-control phase (small positive values)
        for x in [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]:
            ph.update(x, s)
        # Sustained upward shift (Page-Hinkley detects increases)
        fired = False
        for x in [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0]:
            r = ph.update(x, s)
            if r.alarm:
                fired = True
                break
        self.assertTrue(fired)


class TestBocpd(unittest.TestCase):
    def test_quiet_under_stable_data(self):
        b = Bocpd(hazard=1/200, alarm_prob=0.60,
                  prior_mu=0.0, prior_kappa=1.0,
                  prior_alpha=2.0, prior_beta=0.5)
        state = b.init_state()
        for x in [0.01, -0.02, 0.0, 0.03, -0.01, 0.02, 0.0, -0.01, 0.01]:
            r = b.update(x, state)
            self.assertFalse(r.alarm)

    def test_alarm_on_run_length_collapse(self):
        b = Bocpd(hazard=1/200, alarm_prob=0.60,
                  prior_mu=0.0, prior_kappa=1.0,
                  prior_alpha=2.0, prior_beta=0.02)
        state = b.init_state()
        # Stable regime around 0.0
        for x in [0.0, 0.01, -0.02, 0.0, 0.01, -0.01, 0.02, 0.0, 0.01, -0.01]:
            b.update(x, state)
        # Sudden jump
        fired = False
        for x in [1.0, 1.1, 1.05]:
            r = b.update(x, state)
            if r.alarm:
                fired = True
                break
        self.assertTrue(fired, "BOCPD should detect run-length collapse on regime shift")


if __name__ == "__main__":
    unittest.main()
