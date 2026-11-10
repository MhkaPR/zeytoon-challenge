"""Per-cluster intent explanations."""

from __future__ import annotations

import numpy as np

from apps.recommendations import conf
from apps.recommendations.services.v1.eligibility import eligible_rows
from apps.recommendations.services.v1.intent_patterns import (
    FALLBACK_KEY,
    REAL_PATTERN_KEYS,
    build_intent_features,
    message_for,
    pattern_matches,
)
from apps.recommendations.services.v1.intent_scoring import (
    IntentScore,
    best_score,
    evaluate_patterns,
)
from apps.recommendations.services.v1.recommender import Recommender


class IntentExplainer:
    """Detects one intent per interest cluster from the loaded plan space."""

    def __init__(self, bundle):
        self.bundle = bundle
        self.values = bundle["values"]
        self.masks = bundle["masks"]
        self.ids = bundle["ids"]
        self.published_at = bundle["published_at"]
        self.total = self.values.shape[0]
        self.eligible = eligible_rows(bundle)
        self.features = build_intent_features(bundle)
        self.pattern_rows = {
            key: {
                row
                for row, features in enumerate(self.features)
                if pattern_matches(key, features)
            }
            for key in REAL_PATTERN_KEYS
        }

    def explain_all(self, clusters, signals=None, selected_plan_ids=None):
        states = list(clusters.states)
        if not states:
            return []
        positions = [state.x for state in states]
        clicks_by_cluster = self._click_rows_by_cluster(signals or [], positions)
        plans_by_cluster = self._plans_by_cluster(
            selected_plan_ids or [], positions
        )
        explanations = [
            self.explain_cluster(
                state.x,
                cluster_id,
                clicks_by_cluster.get(cluster_id, []),
                plans_by_cluster.get(cluster_id, []),
            )
            for cluster_id, state in enumerate(states)
        ]
        return self._merge_repeated_intents(explanations)

    def explain_cluster(self, position, cluster_id, click_rows, plan_ids=None):
        distances = Recommender.distances(self.values, self.masks, position)
        distances = np.where(self.eligible, distances, np.inf)
        ordered = Recommender.order(self.ids, distances, self.published_at)
        row_of = {plan_id: index for index, plan_id in enumerate(self.ids)}
        limit = max(conf.explain_k(), 1)
        candidate_ids = [
            plan_id
            for plan_id in ordered
            if self.eligible[row_of[plan_id]]
        ][:limit]
        candidate_rows = {
            row_of[plan_id] for plan_id in candidate_ids if plan_id in row_of
        }
        representative = candidate_ids[0] if candidate_ids else None
        if not candidate_rows:
            return self._exploring(cluster_id, representative, plan_ids)

        scores = evaluate_patterns(candidate_rows, self.pattern_rows, self.total)
        if not conf.explain_negative_enabled():
            scores = [score for score in scores if score.direction == "positive"]
        scores = [
            score for score in scores if self._aligns(score.key, click_rows)
        ]
        winner = best_score(scores)
        if winner is None:
            return self._exploring(cluster_id, representative, plan_ids)
        return self._serialize(cluster_id, representative, winner, plan_ids)

    @staticmethod
    def _merge_repeated_intents(explanations):
        """Keep one row per intent and never repeat a plan across rows."""
        merged = {}
        order = []
        used_plans = set()
        for explanation in explanations:
            key = (explanation["intent"], explanation["direction"])
            plan_ids = [
                plan_id
                for plan_id in explanation.get("plan_ids") or []
                if plan_id not in used_plans
            ]
            used_plans.update(plan_ids)
            if key not in merged:
                merged[key] = {**explanation, "plan_ids": plan_ids}
                order.append(key)
            else:
                merged[key]["plan_ids"].extend(plan_ids)
        return [merged[key] for key in order]

    def _plans_by_cluster(self, plan_ids, positions):
        row_of = {plan_id: index for index, plan_id in enumerate(self.ids)}
        grouped = {index: [] for index in range(len(positions))}
        for plan_id in plan_ids:
            row = row_of.get(plan_id)
            if row is None:
                continue
            distances = [
                float(
                    Recommender.distances(
                        self.values[[row]], self.masks[[row]], position
                    )[0]
                )
                for position in positions
            ]
            grouped[int(np.argmin(distances))].append(plan_id)
        return grouped

    def _click_rows_by_cluster(self, signals, positions):
        row_of = {plan_id: index for index, plan_id in enumerate(self.ids)}
        clicked_rows: list[int] = []
        for signal in signals:
            if getattr(signal, "kind", None) != "destination_visit":
                continue
            for plan_id in getattr(signal, "plan_ids", []) or []:
                row = row_of.get(plan_id)
                if row is not None:
                    clicked_rows.append(row)
        grouped = {index: [] for index in range(len(positions))}
        for row in clicked_rows:
            distances = [
                float(
                    Recommender.distances(
                        self.values[[row]], self.masks[[row]], position
                    )[0]
                )
                for position in positions
            ]
            grouped[int(np.argmin(distances))].append(row)
        return grouped

    def _aligns(self, key: str, click_rows: list[int]) -> bool:
        if len(click_rows) < conf.explain_min_clicks():
            return False
        features = [self.features[row] for row in click_rows]
        if key == "cheap":
            values = [
                item.price_pct
                for item in features
                if item.price_pct is not None
            ]
            return bool(values) and sum(values) / len(values) < 0.40
        if key == "spec_heavy":
            values = [
                item.spec_pct for item in features if item.spec_pct is not None
            ]
            return bool(values) and sum(values) / len(values) > 0.60
        if key == "value":
            values = [
                item.spec_pct - item.price_pct
                for item in features
                if item.spec_pct is not None and item.price_pct is not None
            ]
            return bool(values) and sum(values) / len(values) > 0.10
        if key == "premium":
            values = [
                item.price_pct
                for item in features
                if item.price_pct is not None
            ]
            return bool(values) and sum(values) / len(values) > 0.60
        return True

    @staticmethod
    def _serialize(cluster_id, representative, winner: IntentScore, plan_ids):
        return {
            "cluster_id": cluster_id,
            "representative_plan_id": representative,
            "plan_ids": list(plan_ids or []),
            "intent": winner.key,
            "direction": winner.direction,
            "message": message_for(winner.key, winner.direction),
            "confidence": winner.confidence(),
        }

    @staticmethod
    def _exploring(cluster_id, representative, plan_ids=None):
        return {
            "cluster_id": cluster_id,
            "representative_plan_id": representative,
            "plan_ids": list(plan_ids or []),
            "intent": FALLBACK_KEY,
            "direction": None,
            "message": message_for(FALLBACK_KEY),
            "confidence": None,
        }


__all__ = ["IntentExplainer"]
