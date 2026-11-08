"""Ranking facade used by the catalog."""

from __future__ import annotations

import numpy as np

from apps.recommendations.models import InterestProfile
from apps.recommendations.services.v1.recommender import Recommender
from apps.recommendations.services.v1.state import InterestClusters
from apps.recommendations.services.v1.store import PlanSpaceProvider


class RankingService:
    """Orders candidate plans by distance to the viewer's preference."""

    def __init__(self, provider=None, recommender=None):
        self.provider = provider or PlanSpaceProvider()
        self.recommender = recommender or Recommender()

    def rank(self, records, candidate_ids, visitor_id=None, user=None):
        bundle = self.provider.load(records)
        row_of = {plan_id: index for index, plan_id in enumerate(bundle["ids"])}
        candidates = [
            row_of[plan_id] for plan_id in candidate_ids if plan_id in row_of
        ]
        if not candidates:
            return []

        profile = self._profile(visitor_id, user)
        clusters = InterestClusters.from_profile(profile, bundle)
        nearest, distances = clusters.nearest_clusters(
            bundle["values"][candidates], bundle["masks"][candidates]
        )
        cluster_ranks = clusters.cluster_ranks(nearest, distances)
        ordered = self.recommender.order_by_cluster(
            [bundle["ids"][index] for index in candidates],
            distances,
            [bundle["published_at"][index] for index in candidates],
            cluster_ranks,
        )
        return ordered

    def suggest(self, records, visitor_id=None, user=None, per_cluster=5):
        """Return the most relevant plans from each cluster, newest activity first."""
        bundle = self.provider.load(records)
        profile = self._profile(visitor_id, user)
        clusters = InterestClusters.from_profile(profile, bundle, cold_start=False)
        if not clusters.states:
            return []

        matrix = clusters.cluster_distances(bundle["values"], bundle["masks"])
        plan_ids = bundle["ids"]
        published_at = bundle["published_at"]
        suggested = []
        seen = set()
        for cluster_index in clusters.activity_order():
            distances = matrix[:, cluster_index]
            rows = [
                index for index in range(len(plan_ids)) if np.isfinite(distances[index])
            ]
            ordered = self.recommender.order(
                [plan_ids[index] for index in rows],
                [distances[index] for index in rows],
                [published_at[index] for index in rows],
            )
            for plan_id in ordered[: max(int(per_cluster), 0)]:
                if plan_id in seen:
                    continue
                seen.add(plan_id)
                suggested.append(plan_id)
        return suggested

    @staticmethod
    def _profile(visitor_id, user):
        if user is not None and getattr(user, "pk", None):
            return InterestProfile.objects.filter(user=user).first()
        if visitor_id:
            return InterestProfile.objects.filter(visitor_id=visitor_id).first()
        return None
