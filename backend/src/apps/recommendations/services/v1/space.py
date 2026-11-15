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
        self.n_bins = int(n_bins)
        self.edges = self._edges(values, n_bins)
        self.min = float(values.min()) if values.size else None
        self.max = float(values.max()) if values.size else None

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

    def revert(self, x, width=0.0):
        """Approximate the real value range a normalized position ``x`` maps to.

        Inverts ``scale``: a normalized value ``x`` was produced as
        ``index / len(edges)`` where ``index`` is the bin the real value fell
        into. The returned range is that bin's real-value interval, widened by
        ``width`` (a fraction of the interval width) and clamped to the observed
        min/max. When no values were observed, returns ``(None, None)``.
        """
        if self.min is None or self.max is None:
            return None, None
        span = self.max - self.min
        if self.edges.size == 0 or span == 0:
            center = self.min if span == 0 else self.min + float(x) * span
            pad = max(span * float(width), abs(center) * float(width))
            return max(self.min, center - pad), min(self.max, center + pad)
        boundaries = np.concatenate(([self.min], self.edges, [self.max]))
        position = float(np.clip(x, 0.0, 1.0))
        # ``scale`` divides the bin index by the edge count, so invert that here
        # instead of comparing the normalized position to real-unit edges.
        index = int(round(position * len(self.edges)))
        index = max(index, 0)
        index = min(index, len(boundaries) - 2)
        low = float(boundaries[index])
        high = float(boundaries[index + 1])
        if high < low:
            low, high = high, low
        # Quote a small range around the bin's midpoint, proportional to the
        # value. Using the bin width would explode on skewed dimensions (the top
        # price bin can span billions), which is what made the range look like
        # the whole catalogue.
        center = (low + high) / 2.0
        pad = max(abs(center) * float(width), (high - low) * float(width) * 0.1)
        return max(self.min, center - pad), min(self.max, center + pad)

    def revert_interpolated(self, normalized_value, pairs):
        """Map a normalized position back to a real value by interpolation.

        ``pairs`` is an iterable of ``(normalized, raw)`` observations from the
        catalogue. Plans that share a normalized value (quantile bins are
        discrete) are collapsed to their median raw value first, then the real
        value is linearly interpolated between the two nearest distinct points.
        This never invents a phantom bin center: it only returns values that lie
        between real, observed plan values.
        """
        grouped: dict[float, list[float]] = {}
        for normalized, raw in pairs:
            if raw is None:
                continue
            try:
                grouped.setdefault(float(normalized), []).append(float(raw))
            except (TypeError, ValueError):
                continue
        if not grouped:
            return None
        points = sorted(
            (position, float(np.median(values)))
            for position, values in grouped.items()
        )
        x = float(normalized_value)
        if x <= points[0][0]:
            return points[0][1]
        if x >= points[-1][0]:
            return points[-1][1]
        for (low_x, low_value), (high_x, high_value) in zip(points, points[1:]):
            if low_x <= x <= high_x:
                if high_x == low_x:
                    return low_value
                ratio = (x - low_x) / (high_x - low_x)
                return low_value + ratio * (high_value - low_value)
        return points[-1][1]

    def to_payload(self):
        return {
            "n_bins": self.n_bins,
            "edges": self.edges.tolist(),
            "min": self.min,
            "max": self.max,
        }

    @classmethod
    def from_payload(cls, payload):
        binner = cls([], payload.get("n_bins", 5))
        binner.edges = np.asarray(payload.get("edges", []), dtype=float)
        binner.min = payload.get("min")
        binner.max = payload.get("max")
        return binner


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

    def to_scales(self):
        """Serializable value scales needed to revert normalized dimensions.

        Only binners, categorical vocabularies, and names are stored; the fitted
        semantic encoder is not needed to read the space (values/masks are
        persisted directly), so it is omitted to keep rows small.
        """
        return {
            "n_bins": self.n_bins,
            "names": list(self.names),
            "semantic_dimensions": self.semantic.dimensions,
            "binners": {
                field: binner.to_payload() for field, binner in self.binners.items()
            },
            "categories": {field: list(v) for field, v in self.categories.items()},
        }

    @classmethod
    def from_scales(cls, scales):
        """Reconstruct a space for reading (``prior`` + dimension names + revert).

        The semantic encoder is replaced by a dimension-count stub because reads
        use the persisted values/masks and never re-fit titles.
        """
        space = cls(n_bins=int(scales.get("n_bins", 5)))
        space.names = list(scales.get("names", []))
        space.binners = {
            field: NumericBinner.from_payload(payload)
            for field, payload in (scales.get("binners") or {}).items()
        }
        space.categories = {
            field: list(values) for field, values in (scales.get("categories") or {}).items()
        }
        space.semantic.dimensions = int(scales.get("semantic_dimensions", 0))
        return space
