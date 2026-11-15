"""Persisted fitted plan space with a Redis read-through cache.

The space is the source of truth in PostgreSQL (``RecommendationSpace``); Redis
is only a cache in front of it. Profile persistence is done with the Django ORM
directly in the services; per backend-rules §6 there is no repository
abstraction over the ORM.
"""

from __future__ import annotations

import numpy as np
from django.core.cache import cache
from django.db import transaction

from apps.recommendations import conf
from apps.recommendations.models import RecommendationSpace
from apps.recommendations.services.v1.features import PlanFeatureMapper
from apps.recommendations.services.v1.space import PlanSpace

SPACE_KEY = "recommendations:space:v1:{version}"


class PlanSpaceProvider:
    """Loads the plan space through Redis, falling back to the DB, and fits on miss."""

    def __init__(self, mapper=None):
        self.mapper = mapper or PlanFeatureMapper()

    def load(self, records):
        features = [self.mapper.map(record) for record in records]
        version = PlanSpace(n_bins=conf.n_bins()).version(features)
        key = SPACE_KEY.format(version=version)
        cached = cache.get(key)
        if cached is not None and cached.get("raw"):
            return cached

        stored = self._load_persisted(version)
        if stored is not None and stored.get("raw"):
            cache.set(key, stored, conf.space_cache_ttl())
            return stored

        bundle = self._build(features, version)
        self._persist(bundle)
        cache.set(key, bundle, conf.space_cache_ttl())
        return bundle

    def refresh(self, records):
        """Force a fit and persist; a failure leaves the previous active row intact."""
        features = [self.mapper.map(record) for record in records]
        version = PlanSpace(n_bins=conf.n_bins()).version(features)
        bundle = self._build(features, version)
        self._persist(bundle)
        cache.set(SPACE_KEY.format(version=version), bundle, conf.space_cache_ttl())
        return bundle

    def _load_persisted(self, version):
        row = RecommendationSpace.objects.filter(
            version=version, is_active=True
        ).first()
        if row is None:
            return None
        return self._bundle_from_row(row)

    @staticmethod
    def _bundle_from_row(row):
        return {
            "version": row.version,
            "space": PlanSpace.from_scales(row.scales or {}),
            "values": np.asarray(row.values, dtype=float),
            "masks": np.asarray(row.masks, dtype=float),
            "ids": list(row.plan_ids or []),
            "published_at": list(row.published_at or []),
            "raw": row.raw_values or {},
        }

    @staticmethod
    def _persist(bundle):
        """Persist a freshly built bundle and make it the active version.

        The write is transactional so a failure cannot leave two active rows or a
        half-written space; the previous active row stays active on failure.
        """
        with transaction.atomic():
            RecommendationSpace.objects.filter(is_active=True).update(is_active=False)
            RecommendationSpace.objects.update_or_create(
                version=bundle["version"],
                defaults={
                    "names": list(bundle["space"].names),
                    "values": bundle["values"].tolist(),
                    "masks": bundle["masks"].tolist(),
                    "scales": bundle["space"].to_scales(),
                    "plan_ids": list(bundle["ids"]),
                    "published_at": [
                        value.isoformat() if hasattr(value, "isoformat") else value
                        for value in bundle["published_at"]
                    ],
                    "raw_values": bundle.get("raw", {}),
                    "is_active": True,
                    "plan_count": len(bundle["ids"]),
                },
            )
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
            "raw": {
                field: [feature.get(field) for feature in features]
                for field in PlanSpace.NUMERIC
            },
        }
        return bundle
