"""Cached fitted plan space.

Profile persistence is done with the Django ORM directly in the services; per
backend-rules §6 there is no repository abstraction over the ORM.
"""

from __future__ import annotations

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
        space = PlanSpace(n_bins=conf.n_bins()).fit(features)
        values, masks = space.transform(features)
        bundle = {
            "version": version,
            "space": space,
            "values": values,
            "masks": masks,
            "ids": [feature["id"] for feature in features],
            "published_at": [feature["published_at"] for feature in features],
        }
        cache.set(key, bundle, conf.space_cache_ttl())
        return bundle
