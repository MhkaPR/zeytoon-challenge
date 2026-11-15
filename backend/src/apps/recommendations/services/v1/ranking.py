"""Ranking facade used by the catalog."""

from __future__ import annotations

import numpy as np

from apps.recommendations import conf
from apps.recommendations.models import InterestProfile, InterestSignal
from apps.recommendations.services.v1.eligibility import eligible_rows
from apps.recommendations.services.v1.explain import ExplainService
from apps.recommendations.services.v1.explanation import IntentExplainer
from apps.recommendations.services.v1.intent_patterns import (
    FALLBACK_KEY,
    INTENT_PATTERNS,
    REAL_PATTERN_KEYS,
    build_intent_features,
    message_for,
)
from apps.recommendations.services.v1.rank import RankService
from apps.recommendations.services.v1.recommender import Recommender
from apps.recommendations.services.v1.state import InterestClusters, UserState
from apps.recommendations.services.v1.store import PlanSpaceProvider


class RankingService:
    """Orders candidate plans by distance to the viewer's preference."""

    def __init__(self, provider=None, recommender=None):
        self.provider = provider or PlanSpaceProvider()
        self.recommender = recommender or Recommender()

    def rank(self, records, candidate_ids, visitor_id=None, user=None):
        bundle = self.provider.load(records)
        row_of = {plan_id: index for index, plan_id in enumerate(bundle["ids"])}
        candidates = [row_of[plan_id] for plan_id in candidate_ids if plan_id in row_of]
        if not candidates:
            return []

        profile = self._profile(visitor_id, user)
        clusters = InterestClusters.from_profile(profile, bundle)
        distances = clusters.distances(
            bundle["values"][candidates], bundle["masks"][candidates]
        )
        ordered = self.recommender.order(
            [bundle["ids"][index] for index in candidates],
            distances,
            [bundle["published_at"][index] for index in candidates],
        )
        return ordered

    def suggest(self, records, visitor_id=None, user=None, limit=20):
        """Return ranked plans with one closest plan per interest cluster first.

        Ranking purely by the minimum distance across clusters lets a single
        strong interest fill the whole list. Instead we seed the result with the
        closest plan from each cluster (one each), then fill the remaining slots
        by the overall minimum-distance order.
        """
        bundle = self.provider.load(records)
        profile = self._profile(visitor_id, user)
        clusters = InterestClusters.from_profile(profile, bundle)
        return self._select(bundle, clusters, limit)

    def suggest_with_explanations(self, records, visitor_id=None, user=None, limit=20):
        """Return the suggested plan ids plus one intent explanation per cluster.

        Explanations are computed here, in the same pass that ranks the plans, so the
        plan shown in a card and the plan an explanation describes can never
        drift to different versions or profiles.
        """
        bundle = self.provider.load(records)
        profile = self._profile(visitor_id, user)
        clusters = InterestClusters.from_profile(profile, bundle)
        plan_ids = self._select(bundle, clusters, limit)
        signals = []
        if (
            profile is not None
            and profile.signal_count > 0
            and profile.space_version == bundle["version"]
        ):
            signals = list(
                InterestSignal.objects.filter(
                    profile=profile,
                    kind__in=(
                        InterestSignal.Kind.DESTINATION_VISIT,
                        InterestSignal.Kind.DETAILS_VIEW,
                        InterestSignal.Kind.SEARCH_IMPRESSION,
                    ),
                )
            )
        explanations = IntentExplainer(bundle).explain_all(clusters, signals, plan_ids)
        if not explanations or all(
            item.get("intent") == FALLBACK_KEY for item in explanations
        ):
            service_explanations = self._explain_with_service(bundle, plan_ids, profile)
            if service_explanations:
                explanations = service_explanations
        return {"plan_ids": plan_ids, "explanations": explanations}

    def _explain_with_service(self, bundle, plan_ids, profile):
        """Apply the configured pattern thresholds to the surfaced plans."""
        owner_id = self._owner_id(profile)
        if owner_id is None or not plan_ids:
            return []
        selected = set(plan_ids)
        ranked = RankService(node_repository=None).rank(
            owner_id,
            _StaticSpaceProvider(bundle),
            [],
            float("inf"),
        )
        features = build_intent_features(bundle)
        by_id = dict(zip(bundle["ids"], features))
        for interest in ranked:
            interest.plans = [
                plan for plan in interest.plans if plan.plan_id in selected
            ]
            for plan in interest.plans:
                plan.features = by_id[plan.plan_id]
        ranked = [interest for interest in ranked if interest.plans]
        if not ranked:
            return []
        patterns = [
            (
                key,
                lambda plan, key=key: INTENT_PATTERNS[key].matches(plan.features),
            )
            for key in REAL_PATTERN_KEYS
        ]
        matched = ExplainService.explain(ranked, patterns, conf.pattern_thresholds())
        if not matched:
            return []
        order = {key: index for index, key in enumerate(REAL_PATTERN_KEYS)}
        key = sorted(
            matched,
            key=lambda name: (-len(matched[name]), order.get(name, 999)),
        )[0]
        plans = matched[key]
        return [
            {
                "cluster_id": 0,
                "representative_plan_id": plans[0].plan_id,
                "plan_ids": [plan.plan_id for plan in plans],
                "intent": key,
                "direction": "positive",
                "message": message_for(key, "positive"),
                "confidence": None,
            }
        ]

    @staticmethod
    def _owner_id(profile):
        if profile is None:
            return None
        if profile.user_id:
            return profile.user_id
        return profile.visitor_id

    def _select(self, bundle, clusters, limit):
        limit = max(int(limit), 0)
        if limit == 0:
            return []

        eligible = eligible_rows(bundle)
        eligible_ids = {
            plan_id
            for plan_id, is_eligible in zip(bundle["ids"], eligible)
            if is_eligible
        }
        states = clusters.active_states()
        if not states:
            prior = bundle["space"].prior(bundle["values"], bundle["masks"])
            states = [UserState(prior)]
        selected: list[int] = []
        seen: set[int] = set()
        for state in states:
            distances = self.recommender.distances(
                bundle["values"], bundle["masks"], state.x
            )
            distances = np.where(eligible, distances, np.inf)
            ordered = self.recommender.order(
                bundle["ids"], distances, bundle["published_at"]
            )
            for plan_id in ordered:
                if plan_id not in eligible_ids:
                    continue
                if plan_id not in seen:
                    selected.append(plan_id)
                    seen.add(plan_id)
                    break
            if len(selected) >= limit:
                return selected[:limit]

        distances = np.full(bundle["values"].shape[0], np.inf)
        for state in states:
            distances = np.minimum(
                distances,
                self.recommender.distances(bundle["values"], bundle["masks"], state.x),
            )
        distances = np.where(eligible, distances, np.inf)
        ordered = self.recommender.order(
            bundle["ids"], distances, bundle["published_at"]
        )
        for plan_id in ordered:
            if len(selected) >= limit:
                break
            if plan_id not in eligible_ids:
                continue
            if plan_id not in seen:
                selected.append(plan_id)
                seen.add(plan_id)
        return selected[:limit]

    @staticmethod
    def _profile(visitor_id, user):
        if user is not None and getattr(user, "pk", None):
            return InterestProfile.objects.filter(user=user).first()
        if visitor_id:
            profile = InterestProfile.objects.filter(visitor_id=visitor_id).first()
            if profile is None:
                return None
            if profile.merged_into_id:
                # After login the device profile is tombstoned and later signals are
                # redirected to the account profile. Read the account state too, not the
                # frozen pre-merge snapshot, or suggestions ignore everything since login.
                return InterestProfile.objects.filter(
                    user_id=profile.merged_into_id
                ).first()
            return profile
        return None


class _StaticSpaceProvider:
    """Returns an already-loaded bundle without re-fitting or persisting."""

    def __init__(self, bundle):
        self.bundle = bundle

    def load(self, records):
        return self.bundle
