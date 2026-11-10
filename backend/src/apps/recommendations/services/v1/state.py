"""Per-viewer preference state and its Kalman-style update."""

from __future__ import annotations

import numpy as np

from apps.recommendations import conf


class UserState:
    """Preference position plus per-dimension uncertainty."""

    def __init__(
        self,
        position,
        uncertainty=None,
        drift=None,
        s0=None,
        negative=None,
        activity=None,
    ):
        self.x = np.asarray(position, float)
        self.s = (
            np.asarray(uncertainty, float)
            if uncertainty is not None
            else np.full_like(self.x, s0 if s0 is not None else conf.uncertainty())
        )
        self.q = conf.drift() if drift is None else drift
        self.s0 = conf.uncertainty() if s0 is None else s0
        self.neg = conf.negative_factor() if negative is None else negative
        self.activity = 1.0 if activity is None else float(activity)

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


def _masked_distances(values, masks, position):
    diff = (values - np.asarray(position, float)) ** 2
    totals = masks.sum(axis=1)
    safe = np.maximum(totals, 1)
    distance = np.sqrt((diff * masks).sum(axis=1) / safe)
    return np.where(totals > 0, distance, np.inf)


class InterestClusters:
    """A bounded set of interest positions so several themes stay represented.

    ``InterestProfile.position`` may be a flat vector from before this change or a list
    of cluster vectors. A flat vector is treated as one cluster.
    """

    def __init__(
        self,
        positions,
        uncertainties=None,
        activities=None,
        max_clusters=None,
        threshold=None,
    ):
        self.max_clusters = (
            conf.max_interest_clusters() if max_clusters is None else int(max_clusters)
        )
        self.threshold = (
            conf.cluster_distance_threshold()
            if threshold is None
            else float(threshold)
        )
        self.states = self._parse(positions, uncertainties, activities)

    @staticmethod
    def _is_flat(positions):
        if isinstance(positions, np.ndarray):
            return positions.ndim == 1
        if len(positions) == 0:
            return False
        first = positions[0]
        return isinstance(first, (int, float, np.number))

    def _parse(self, positions, uncertainties, activities=None):
        positions = list(positions) if positions is not None else []
        if len(positions) == 0:
            return []
        activities = list(activities) if activities else []
        if self._is_flat(positions):
            return [
                UserState(
                    positions,
                    uncertainties,
                    activity=activities[0] if activities else None,
                )
            ]
        uncertainties = uncertainties or []
        return [
            UserState(
                position,
                uncertainties[index] if index < len(uncertainties) else None,
                activity=activities[index] if index < len(activities) else None,
            )
            for index, position in enumerate(positions)
        ]

    @classmethod
    def from_profile(cls, profile, bundle, cold_start=True):
        dimensions = bundle["values"].shape[1]
        if (
            profile is not None
            and profile.space_version == bundle["version"]
            and cls._matches(profile.position, dimensions)
        ):
            return cls(
                profile.position,
                profile.uncertainty,
                profile.activity_profile,
            )
        if cold_start:
            return cls(bundle["space"].prior(bundle["values"], bundle["masks"]))
        return cls([])

    @staticmethod
    def _matches(position, dimensions):
        if not position:
            return False
        if InterestClusters._is_flat(position):
            return len(position) == dimensions
        return all(len(row) == dimensions for row in position)

    @property
    def positions(self):
        return [[float(value) for value in state.x] for state in self.states]

    @property
    def uncertainties(self):
        return [[float(value) for value in state.s] for state in self.states]

    @property
    def activities(self):
        return [float(state.activity) for state in self.states]

    def active_states(self):
        if not self.states:
            return []
        ordered = sorted(
            self.states, key=lambda state: state.activity, reverse=True
        )
        floor = max(
            conf.cluster_min_activity(),
            ordered[0].activity * conf.cluster_min_activity_ratio(),
        )
        limit = max(conf.suggestion_cluster_limit(), 1)
        return [
            state for state in ordered if state.activity >= floor
        ][:limit]

    def nearest(self, values, masks):
        if not self.states:
            return None, float("inf")
        distances = [
            float(_masked_distances(np.asarray([values]), np.asarray([masks]), state.x)[0])
            for state in self.states
        ]
        index = int(np.argmin(distances))
        return self.states[index], distances[index]

    def update(self, values, masks, noise, sign=1):
        values = np.asarray(values, float)
        masks = np.asarray(masks, float)
        if not np.asarray(masks, bool).any():
            return
        if not self.states:
            state = UserState(values)
            state.update(values, masks, noise, sign)
            self.states.append(state)
            return

        decay = conf.cluster_activity_decay()
        for existing in self.states:
            existing.activity *= decay

        state, distance = self.nearest(values, masks)
        if distance <= self.threshold:
            state.update(values, masks, noise, sign)
            state.activity += 1.0
            return

        new_state = UserState(values)
        new_state.update(values, masks, noise, sign)
        new_state.activity = 1.0
        self.states.append(new_state)

        if len(self.states) > self.max_clusters:
            worst = min(
                range(len(self.states)),
                key=lambda i: (
                    self.states[i].activity,
                    -float(np.mean(self.states[i].s)),
                ),
            )
            self.states.pop(worst)

    def distances(self, values, masks):
        values = np.asarray(values, float)
        masks = np.asarray(masks, float)
        if not self.states:
            return np.full(values.shape[0], np.inf)
        result = np.full(values.shape[0], np.inf)
        for state in self.states:
            result = np.minimum(result, _masked_distances(values, masks, state.x))
        return result

    def idle(self, days, gap=0.05):
        for state in self.states:
            state.idle(days, gap)
