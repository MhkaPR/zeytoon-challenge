"""Kalman arithmetic for node position and uncertainty.

This module is the only place that mutates a node's ``position`` or
``uncertainty``. Every other recommendation module delegates here.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from apps.recommendations import conf


class KalmanModule:
    """Decay and update a single node's state."""

    @staticmethod
    def decay(
        position,
        uncertainty,
        last_updated_at: datetime | None,
        now: datetime | None = None,
        decay_rate: float | None = None,
        max_uncertainty: float | None = None,
    ):
        """Grow uncertainty with elapsed time and clamp it.

        Returns ``(position, uncertainty, decayed_uncertainty)``. Position is
        returned unchanged so callers can feed the triple straight into
        :meth:`update`.
        """
        current = np.asarray(position, float).copy()
        unc = np.asarray(uncertainty, float).copy()
        moment = now or datetime.now(timezone.utc)
        elapsed_hours = 0.0
        if last_updated_at is not None:
            last = last_updated_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            elapsed_hours = max((moment - last).total_seconds() / 3600.0, 0.0)
        rate = (
            conf.kalman_decay_rate_per_hour()
            if decay_rate is None
            else float(decay_rate)
        )
        cap = (
            conf.kalman_max_uncertainty()
            if max_uncertainty is None
            else float(max_uncertainty)
        )
        decayed = np.minimum(unc + rate * elapsed_hours, cap)
        return current, decayed, decayed

    @staticmethod
    def update(
        position,
        uncertainty,
        observation,
        mask=None,
        weight: float | None = None,
        process_noise: float | None = None,
        measurement_noise: float | None = None,
        sign: int = 1,
        negative_factor: float | None = None,
    ):
        """Apply one observation and return the new ``(position, uncertainty)``."""
        x = np.asarray(position, float).copy()
        s = np.asarray(uncertainty, float).copy()
        values = np.asarray(observation, float)
        active = np.ones_like(x, dtype=bool) if mask is None else np.asarray(mask, bool)
        if not active.any():
            return x, s

        q = (
            conf.kalman_process_noise()
            if process_noise is None
            else float(process_noise)
        )
        base_noise = (
            conf.kalman_measurement_noise()
            if measurement_noise is None
            else float(measurement_noise)
        )
        noise = base_noise if weight is None else base_noise * float(weight)
        noise = max(noise, 1e-6)
        neg = (
            conf.negative_factor()
            if negative_factor is None
            else float(negative_factor)
        )

        s[active] += q
        gain = s[active] / (s[active] + noise)
        factor = 1.0 if sign > 0 else -neg
        x[active] = np.clip(
            x[active] + factor * gain * (values[active] - x[active]), 0, 1
        )
        s[active] = (1 - gain) * s[active]
        return x, s

    @classmethod
    def apply(
        cls,
        position,
        uncertainty,
        observation,
        last_updated_at: datetime | None,
        now: datetime | None = None,
        mask=None,
        weight: float | None = None,
        process_noise: float | None = None,
        measurement_noise: float | None = None,
        sign: int = 1,
        negative_factor: float | None = None,
    ):
        """Decay, then update, returning ``(position, uncertainty, decayed)``."""
        moment = now or datetime.now(timezone.utc)
        decayed_position, decayed_uncertainty, _ = cls.decay(
            position, uncertainty, last_updated_at, now=moment
        )
        new_position, new_uncertainty = cls.update(
            decayed_position,
            decayed_uncertainty,
            observation,
            mask=mask,
            weight=weight,
            process_noise=process_noise,
            measurement_noise=measurement_noise,
            sign=sign,
            negative_factor=negative_factor,
        )
        return new_position, new_uncertainty, decayed_uncertainty

    @staticmethod
    def idle(uncertainty, days, gap=0.05, cap=None):
        """Grow uncertainty during inactivity, bounded by ``cap``."""
        unc = np.asarray(uncertainty, float).copy()
        limit = conf.uncertainty() if cap is None else float(cap)
        return np.minimum(unc + float(gap) * float(days), limit)


__all__ = ["KalmanModule"]
