"""Per-viewer preference state and its Kalman-style update."""

from __future__ import annotations

import time
from datetime import datetime, timezone

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
        last_active=None,
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
        self.last_active = _epoch(last_active)

    def update(self, values, masks, noise, sign=1, when=None):
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
        self.last_active = _epoch(when) or time.time()

    def idle(self, days, gap=0.05):
        self.s = np.minimum(self.s + gap * days, self.s0)


def _epoch(value):
    """Normalise an ISO timestamp, datetime, or epoch to UTC seconds."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


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
        activity=None,
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
        self.states = self._parse(positions, uncertainties, activity)

    @staticmethod
    def _is_flat(positions):
        return bool(positions) and not isinstance(positions[0], (list, tuple))

    def _parse(self, positions, uncertainties, activity):
        positions = list(positions) if positions is not None else []
        if len(positions) == 0:
            return []
        activity = list(activity) if activity is not None else []
        if self._is_flat(positions):
            return [
                UserState(
                    positions,
                    uncertainties,
                    last_active=activity[0] if activity else None,
                )
            ]
        uncertainties = uncertainties or []
        return [
            UserState(
                position,
                uncertainties[index] if index < len(uncertainties) else None,
                last_active=activity[index] if index < len(activity) else None,
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
            clusters = cls(
                profile.position,
                profile.uncertainty,
                profile.activity_profile,
            )
            clusters._hydrate_activity(profile, bundle)
            return clusters
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
    def activity(self):
        return [
            (
                datetime.fromtimestamp(state.last_active, timezone.utc).isoformat()
                if state.last_active is not None
                else None
            )
            for state in self.states
        ]

    def _hydrate_activity(self, profile, bundle):
        """Backfill recency for profiles saved before activity tracking existed."""
        if not self.states or any(
            state.last_active is not None for state in self.states
        ):
            return
        if profile is None or not getattr(profile, "pk", None):
            return
        row_of = {plan_id: index for index, plan_id in enumerate(bundle["ids"])}
        signals = profile.signals.order_by("-created_at").values_list(
            "plan_ids", "created_at"
        )[:100]
        for plan_ids, created_at in signals:
            rows = [row_of[plan_id] for plan_id in (plan_ids or []) if plan_id in row_of]
            if not rows:
                continue
            centroid = bundle["values"][rows].mean(axis=0)
            mask = bundle["masks"][rows].max(axis=0)
            state, _distance = self.nearest(centroid, mask)
            if state is not None and state.last_active is None:
                state.last_active = _epoch(created_at)

    def nearest(self, values, masks):
        if not self.states:
            return None, float("inf")
        distances = [
            float(_masked_distances(np.asarray([values]), np.asarray([masks]), state.x)[0])
            for state in self.states
        ]
        index = int(np.argmin(distances))
        return self.states[index], distances[index]

    def update(self, values, masks, noise, sign=1, when=None):
        values = np.asarray(values, float)
        masks = np.asarray(masks, float)
        if not np.asarray(masks, bool).any():
            return
        if not self.states:
            state = UserState(values)
            state.update(values, masks, noise, sign, when=when)
            self.states.append(state)
            return
        state, distance = self.nearest(values, masks)
        if distance <= self.threshold:
            state.update(values, masks, noise, sign, when=when)
            return
        new_state = UserState(values)
        new_state.update(values, masks, noise, sign, when=when)
        self.states.append(new_state)
        if len(self.states) > self.max_clusters:
            worst = max(
                range(len(self.states)),
                key=lambda index: float(np.mean(self.states[index].s)),
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

    def cluster_distances(self, values, masks):
        """Return a plan-by-cluster matrix of masked distances."""
        values = np.asarray(values, float)
        masks = np.asarray(masks, float)
        if not self.states:
            return np.full((values.shape[0], 0), np.inf)
        return np.column_stack(
            [_masked_distances(values, masks, state.x) for state in self.states]
        )

    def nearest_clusters(self, values, masks):
        """Return each plan's nearest cluster index and its distance."""
        values = np.asarray(values, float)
        matrix = self.cluster_distances(values, masks)
        if matrix.shape[1] == 0:
            return (
                np.zeros(values.shape[0], dtype=int),
                np.full(values.shape[0], np.inf),
            )
        indices = np.argmin(matrix, axis=1)
        distances = matrix[np.arange(matrix.shape[0]), indices]
        return indices, distances

    def activity_order(self):
        """Cluster indices ordered by most recent activity, newest first."""
        return sorted(
            range(len(self.states)),
            key=lambda index: (
                self.states[index].last_active
                if self.states[index].last_active is not None
                else float("-inf"),
                -index,
            ),
            reverse=True,
        )

    def cluster_ranks(self, nearest, distances):
        """Map each plan's nearest cluster to its recency rank."""
        if not self.states:
            return [0] * len(nearest)
        rank_of = {
            cluster_index: rank
            for rank, cluster_index in enumerate(self.activity_order())
        }
        sentinel = len(self.states)
        return [
            rank_of.get(int(index), sentinel) if distance != float("inf") else sentinel
            for index, distance in zip(nearest, distances)
        ]

    def idle(self, days, gap=0.05):
        for state in self.states:
            state.idle(days, gap)
