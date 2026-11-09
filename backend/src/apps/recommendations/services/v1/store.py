"""Cached fitted plan space.

Profile persistence is done with the Django ORM directly in the services; per
backend-rules §6 there is no repository abstraction over the ORM.
"""

from __future__ import annotations

import numpy as np
from django.core.cache import cache

from apps.recommendations import conf
from apps.recommendations.services.v1.features import PlanFeatureMapper
from apps.recommendations.services.v1.space import PlanSpace

SPACE_KEY = "recommendations:space:v1:{version}"


class PlanSpaceProvider:
    """Fits and caches the plan space for one catalogue version."""

    def __init__(self, mapper=None):
        self.mapper = mapper or PlanFeatureMapper()

    def load(self, records):
        features = [self.mapper.map(record) for record in records]
        version = PlanSpace(n_bins=conf.n_bins()).version(features)
        key = SPACE_KEY.format(version=version)
        cached = cache.get(key)
        if cached is not None:
            return cached
        bundle = self._build(features, version)
        cache.set(key, bundle, conf.space_cache_ttl())
        return bundle

    def refresh(self, records):
        """Force a fit and cache write; a failure leaves the previous key intact."""
        features = [self.mapper.map(record) for record in records]
        version = PlanSpace(n_bins=conf.n_bins()).version(features)
        bundle = self._build(features, version)
        cache.set(SPACE_KEY.format(version=version), bundle, conf.space_cache_ttl())
        return bundle

    @staticmethod
    def _build(features, version):
        if not features:
            raise ValueError("cannot fit a recommendation space without plans")
        space = PlanSpace(n_bins=conf.n_bins()).fit(features)
        values, masks = space.transform(features)
        if values.shape != masks.shape:
            raise ValueError("recommendation space values and masks must match")
        if not np.isfinite(values).all() or not np.isfinite(masks).all():
            raise ValueError("recommendation space contains non-finite values")
        bundle = {
            "version": version,
            "space": space,
            "values": values,
            "masks": masks,
            "ids": [feature["id"] for feature in features],
            "published_at": [feature["published_at"] for feature in features],
        }
        return bundle
