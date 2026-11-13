"""Distance and ordering over the plan space."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np


class Recommender:
    """Ranks plans by masked distance to a viewer position."""

    @staticmethod
    def distances(values, masks, position):
        diff = (values - np.asarray(position, float)) ** 2
        weighted = diff * masks
        totals = masks.sum(axis=1)
        safe = np.maximum(totals, 1)
        distance = np.sqrt(weighted.sum(axis=1) / safe)
        return np.where(totals > 0, distance, np.inf)

    @staticmethod
    def order(plan_ids, distances, published_at):
        """Order by distance, then newest first, then id, so pages never repeat."""
        rows = [
            (plan_id, float(distance), _epoch(stamp))
            for plan_id, distance, stamp in zip(plan_ids, distances, published_at)
        ]
        rows.sort(key=lambda row: (row[1], -row[2], row[0]))
        return [row[0] for row in rows]


def _epoch(value):
    """Convert an ISO timestamp to an epoch float; unknown values sort oldest."""
    if not value:
        return 0.0
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()
