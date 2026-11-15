"""Public interface for the recommendations module.

Other modules import recommendation behaviour through this module only.
"""

from apps.recommendations.services.v1.merging import StateMerger
from apps.recommendations.services.v1.explain import ExplainService
from apps.recommendations.services.v1.rank import RankService
from apps.recommendations.services.v1.record import RecordService
from apps.recommendations.services.v1.ranking import RankingService
from apps.recommendations.services.v1.signals import SignalRecorder


class RecommendationsInterface:
    """The single sanctioned entry point into the recommendations module."""

    @staticmethod
    def rank(records, candidate_ids, visitor_id=None, user=None):
        return RankingService().rank(
            records, candidate_ids, visitor_id=visitor_id, user=user
        )

    @staticmethod
    def suggest(records, visitor_id=None, user=None, limit=20):
        return RankingService().suggest(
            records,
            visitor_id=visitor_id,
            user=user,
            limit=limit,
        )

    @staticmethod
    def suggest_with_explanations(records, visitor_id=None, user=None, limit=20):
        return RankingService().suggest_with_explanations(
            records,
            visitor_id=visitor_id,
            user=user,
            limit=limit,
        )

    @staticmethod
    def record_signals(records, kind, plan_ids, query="", visitor_id=None, user=None):
        return SignalRecorder().record(
            records,
            kind,
            plan_ids,
            query=query,
            visitor_id=visitor_id,
            user=user,
        )

    @staticmethod
    def merge_on_login(user, visitor_id):
        return StateMerger.merge_on_login(user, visitor_id)

    @staticmethod
    def clear_visitor(visitor_id):
        return StateMerger.clear_visitor(visitor_id)

    @staticmethod
    def rank_nodes(owner_id, records, threshold=None, provider=None):
        from apps.recommendations import conf
        from apps.recommendations.services.v1.store import PlanSpaceProvider

        return RankService().rank(
            owner_id,
            provider or PlanSpaceProvider(),
            records,
            conf.rank_threshold() if threshold is None else threshold,
        )

    @staticmethod
    def record_interaction(owner_id, interaction, provider=None):
        from apps.recommendations.services.v1.store import PlanSpaceProvider

        return RecordService().record(
            owner_id, interaction, provider or PlanSpaceProvider()
        )

    @staticmethod
    def explain_ranked(ranked_interests, patterns, thresholds):
        return ExplainService.explain(ranked_interests, patterns, thresholds)


__all__ = ["RecommendationsInterface"]
