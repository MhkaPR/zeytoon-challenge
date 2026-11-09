"""Discretised plan space with existence masks.

Every plan is a point in ``[0, 1]^d``. Each dimension carries a mask so a plan is only
compared on attributes it actually declares.
"""

from __future__ import annotations

import hashlib

import numpy as np

from apps.recommendations.services.v1.semantic import SemanticEncoder


class NumericBinner:
    """Maps numeric values to ``[0, 1]`` using quantile edges."""

    def __init__(self, values, n_bins):
        values = np.asarray([v for v in values if v is not None], dtype=float)
        self.edges = self._edges(values, n_bins)

    @staticmethod
    def _edges(values, n_bins):
        if values.size == 0:
            return np.array([], dtype=float)
        unique = np.unique(values)
        if unique.size == 1:
            return np.array([], dtype=float)
        quantiles = np.linspace(0, 1, max(int(n_bins), 2))
        edges = np.unique(np.quantile(values, quantiles))
        return edges[1:-1] if edges.size > 2 else edges

    def scale(self, value):
        if value is None:
            return 0.0
        if self.edges.size == 0:
            return 0.5
        index = int(np.searchsorted(self.edges, float(value), side="right"))
        return index / max(self.edges.size, 1)


class PlanSpace:
    """Fitted space: numeric binners plus categorical vocabularies."""

    NUMERIC = ("price", "cpu", "ram", "disk", "traffic")
    CATEGORICAL = ("country", "os")

    def __init__(self, n_bins=5):
        self.n_bins = n_bins
        self.binners = {}
        self.categories = {}
        self.names = []
        self.semantic = SemanticEncoder()

    def fit(self, features):
        self.semantic.fit([item.get("title") for item in features])
        for field in self.NUMERIC:
            self.binners[field] = NumericBinner(
                [item.get(field) for item in features], self.n_bins
            )
        for field in self.CATEGORICAL:
            values = {item.get(field) for item in features if item.get(field)}
            self.categories[field] = sorted(values)
        self.names = self._names()
        return self

    def _names(self):
        names = ["price"]
        for field in ("cpu", "ram", "disk", "traffic"):
            names.extend([f"has_{field}", field])
        for field in self.CATEGORICAL:
            names.append(f"has_{field}")
            names.extend(f"{field}={value}" for value in self.categories[field])
        names.extend(f"semantic_{index}" for index in range(self.semantic.dimensions))
        return names

    def transform(self, features):
        rows, masks = [], []
        for item in features:
            values, mask = [], []
            price = item.get("price")
            values.append(self.binners["price"].scale(price))
            mask.append(1.0 if price is not None else 0.0)
            for field in ("cpu", "ram", "disk", "traffic"):
                present = item.get(field) is not None
                values.append(1.0 if present else 0.0)
                mask.append(1.0)
                values.append(self.binners[field].scale(item.get(field)))
                mask.append(1.0 if present else 0.0)
            for field in self.CATEGORICAL:
                value = item.get(field)
                present = bool(value)
                values.append(1.0 if present else 0.0)
                mask.append(1.0)
                for category in self.categories[field]:
                    values.append(1.0 if value == category else 0.0)
                    mask.append(1.0 if present else 0.0)
            semantic_values, semantic_masks = self.semantic.transform(
                [item.get("title")]
            )
            values.extend(semantic_values[0].tolist())
            mask.extend(semantic_masks[0].tolist())
            rows.append(values)
            masks.append(mask)
        return np.asarray(rows, float), np.asarray(masks, float)

    def prior(self, values, masks):
        totals = masks.sum(axis=0)
        return np.where(
            totals > 0,
            (values * masks).sum(axis=0) / np.maximum(totals, 1),
            0.5,
        )

    def version(self, features):
        stamps = [item.get("published_at") for item in features if item.get("published_at")]
        latest = max(stamps) if stamps else ""
        safe = "".join(ch for ch in str(latest) if ch.isalnum())
        titles = "|".join(
            f"{item.get('id')}:{item.get('title') or ''}" for item in features
        )
        digest = hashlib.sha1(titles.encode("utf-8")).hexdigest()[:12]
        semantic = self.semantic
        config = (
            f"{semantic.dimensions}-{semantic.n_features}-"
            f"{semantic.ngram_range[0]}-{semantic.ngram_range[1]}-"
            f"{semantic.random_state}"
        )
        return f"{safe}-{len(features)}-{digest}-{config}"
