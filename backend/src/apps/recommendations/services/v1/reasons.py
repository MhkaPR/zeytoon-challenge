"""Feature attribution: why does the suggested plan set match one interest cluster?

For every interest cluster we take the ``k`` nearest plans in the shared
normalized space (the candidate set ``R``). A feature "explains" the
recommendation when the plans that fall inside the feature's ``[P5, P95]`` band
overlap heavily with ``R``. We score that overlap with F1 (precision = share of
the band that is in ``R``; recall = share of ``R`` that is in the band) so a
feature that is both precise and covers the candidate set wins.

The six technical features (price/cpu/ram/disk/traffic + the best categorical
country/os value) and one textual super-feature (the mean F1 of the ten semantic
dimensions) compete on the same scale. The top ``N`` features above the F1
threshold become the explanation. Numeric bounds are reverted to real units by
interpolating between observed plan values, never by quoting a bin center.
"""

from __future__ import annotations

import numpy as np

from apps.recommendations import conf
from apps.recommendations.services.v1.recommender import Recommender

NUMERIC_FIELDS = ("price", "cpu", "ram", "disk", "traffic")
NUMERIC_UNITS = {
    "price": "IRR",
    "cpu": "core",
    "ram": "GB",
    "disk": "GB",
    "traffic": "GB",
}
CATEGORICAL_FIELDS = ("country", "os")
TEXTUAL_FEATURE = "textual_category"


def _f1(inter: int, band_size: int, candidate_size: int) -> float:
    if inter <= 0 or band_size <= 0 or candidate_size <= 0:
        return 0.0
    precision = inter / band_size
    recall = inter / candidate_size
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


class FeatureReasoner:
    """Computes per-cluster feature reasons from a loaded plan-space bundle."""

    def __init__(self, bundle):
        self.bundle = bundle
        self.values = bundle["values"]
        self.masks = bundle["masks"]
        self.names = bundle["space"].names
        self.categories = bundle["space"].categories
        self.binners = bundle["space"].binners
        self.raw = bundle.get("raw") or {}
        self.ids = bundle["ids"]
        self.total = self.values.shape[0]
        self._points_cache: dict[str, list[tuple[float, float | None]]] = {}

    def explain_all(self, clusters):
        """Return one explanation per interest cluster that has reasons."""
        explanations = []
        for cluster_id, state in enumerate(clusters.states):
            explanation = self.explain_cluster(state.x, cluster_id)
            if explanation["reasons"]:
                explanations.append(explanation)
        return explanations

    def explain_cluster(self, position, cluster_id):
        distances = Recommender.distances(self.values, self.masks, position)
        ordered = Recommender.order(self.ids, distances, self.bundle["published_at"])
        row_of = {plan_id: index for index, plan_id in enumerate(self.ids)}
        limit = max(conf.explain_k(), 1)
        candidates = [row_of[plan_id] for plan_id in ordered[:limit]]
        representative = self.ids[candidates[0]] if candidates else None
        return {
            "cluster_id": cluster_id,
            "representative_plan_id": representative,
            "reasons": self._reasons(candidates),
        }

    def _reasons(self, candidates):
        if not candidates:
            return []
        candidate_set = set(candidates)
        candidate_size = len(candidate_set)
        scored = []
        scored.extend(self._numeric_scores(candidate_set, candidate_size))
        scored.extend(self._categorical_scores(candidate_set, candidate_size))
        textual = self._textual_score(candidate_set, candidate_size)
        if textual is not None:
            scored.append(textual)

        threshold = conf.explain_f1_threshold()
        scored = [item for item in scored if item["f1"] >= threshold]
        scored.sort(key=lambda item: (-item["f1"], item["feature"]))
        scored = scored[: max(conf.explain_top_n(), 0)]
        return [self._serialize(item) for item in scored]

    def _band_score(self, index, candidate_set, candidate_size):
        present = [
            row for row in candidate_set if self.masks[row][index] > 0
        ]
        if not present:
            return None
        values = [float(self.values[row][index]) for row in present]
        low = float(np.percentile(values, conf.explain_percentile_lo()))
        high = float(np.percentile(values, conf.explain_percentile_hi()))
        in_band = [
            row
            for row in range(self.total)
            if self.masks[row][index] > 0
            and low <= float(self.values[row][index]) <= high
        ]
        inter = [row for row in in_band if row in candidate_set]
        score = _f1(len(inter), len(in_band), candidate_size)
        return low, high, score

    def _numeric_scores(self, candidate_set, candidate_size):
        scores = []
        for field in NUMERIC_FIELDS:
            if field not in self.names:
                continue
            index = self.names.index(field)
            result = self._band_score(index, candidate_set, candidate_size)
            if result is None:
                continue
            low, high, score = result
            if score <= 0:
                continue
            scores.append(
                {
                    "feature": field,
                    "type": "numeric",
                    "f1": score,
                    "norm_range": (low, high),
                }
            )
        return scores

    def _categorical_scores(self, candidate_set, candidate_size):
        best = None
        for field in CATEGORICAL_FIELDS:
            for category in self.categories.get(field, []):
                name = f"{field}={category}"
                if name not in self.names:
                    continue
                index = self.names.index(name)
                in_category = [
                    row
                    for row in range(self.total)
                    if self.masks[row][index] > 0
                    and float(self.values[row][index]) == 1.0
                ]
                inter = [row for row in in_category if row in candidate_set]
                score = _f1(len(inter), len(in_category), candidate_size)
                if score <= 0:
                    continue
                if best is None or score > best["f1"]:
                    best = {
                        "feature": field,
                        "type": "categorical",
                        "label": category,
                        "f1": score,
                    }
        return [best] if best is not None else []

    def _textual_score(self, candidate_set, candidate_size):
        semantic = [
            index
            for index, name in enumerate(self.names)
            if name.startswith("semantic_")
        ]
        scores = []
        for index in semantic:
            result = self._band_score(index, candidate_set, candidate_size)
            if result is None:
                continue
            scores.append(result[2])
        if not scores:
            return None
        return {
            "feature": TEXTUAL_FEATURE,
            "type": "textual",
            "f1": float(np.mean(scores)),
        }

    def _points(self, field):
        cached = self._points_cache.get(field)
        if cached is not None:
            return cached
        raw_values = self.raw.get(field) or []
        index = self.names.index(field)
        points = [
            (float(self.values[row][index]), raw_values[row] if row < len(raw_values) else None)
            for row in range(self.total)
        ]
        self._points_cache[field] = points
        return points

    def _serialize(self, item):
        feature = item["feature"]
        payload = {
            "feature": feature,
            "type": item["type"],
            "f1": round(float(item["f1"]), 4),
        }
        if item["type"] == "numeric":
            index = self.names.index(feature)
            binner = self.binners.get(feature)
            points = self._points(feature)
            low_norm, high_norm = item["norm_range"]
            low = (
                binner.revert_interpolated(low_norm, points)
                if binner is not None
                else None
            )
            high = (
                binner.revert_interpolated(high_norm, points)
                if binner is not None
                else None
            )
            if low is not None and high is not None:
                if high < low:
                    low, high = high, low
                payload["real_range"] = [round(low, 1), round(high, 1)]
            payload["unit"] = NUMERIC_UNITS.get(feature)
        elif item["type"] == "categorical":
            payload["label"] = item["label"]
        return payload
