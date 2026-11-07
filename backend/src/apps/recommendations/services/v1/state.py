"""Per-viewer preference state and its Kalman-style update."""

from __future__ import annotations

import numpy as np

from apps.recommendations import conf


class UserState:
    """Preference position plus per-dimension uncertainty."""

    def __init__(self, position, uncertainty=None, drift=None, s0=None, negative=None):
        self.x = np.asarray(position, float)
        self.s = (
            np.asarray(uncertainty, float)
            if uncertainty is not None
            else np.full_like(self.x, s0 if s0 is not None else conf.uncertainty())
        )
        self.q = conf.drift() if drift is None else drift
        self.s0 = conf.uncertainty() if s0 is None else s0
        self.neg = conf.negative_factor() if negative is None else negative

    def update(self, values, masks, noise, sign=1):
        active = np.asarray(masks, bool)
        if not active.any():
            return
        self.s[active] += self.q
        gain = self.s[active] / (self.s[active] + max(float(noise), 1e-6))
        factor = 1.0 if sign > 0 else -self.neg
        self.x[active] = np.clip(
            self.x[active] + factor * gain * (values[active] - self.x[active]), 0, 1
        )
        self.s[active] = (1 - gain) * self.s[active]

    def idle(self, days, gap=0.05):
        self.s = np.minimum(self.s + gap * days, self.s0)
