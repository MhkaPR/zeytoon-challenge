"""Ranking facade used by the catalog."""

from __future__ import annotations

from apps.recommendations.models import InterestProfile
from apps.recommendations.services.v1.recommender import Recommender
from apps.recommendations.services.v1.state import UserState
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

        if user is not None and getattr(user, "pk", None):
            profile = InterestProfile.objects.filter(user=user).first()
        elif visitor_id:
            profile = InterestProfile.objects.filter(visitor_id=visitor_id).first()
        else:
            profile = None
        if (
            profile is not None
            and profile.space_version == bundle["version"]
            and len(profile.position) == bundle["values"].shape[1]
        ):
            state = UserState(profile.position, profile.uncertainty)
            position = state.x
        else:
            position = bundle["space"].prior(bundle["values"], bundle["masks"])

        distances = self.recommender.distances(
            bundle["values"][candidates], bundle["masks"][candidates], position
        )
        ordered = self.recommender.order(
            [bundle["ids"][index] for index in candidates],
            distances,
            [bundle["published_at"][index] for index in candidates],
        )
        return ordered
