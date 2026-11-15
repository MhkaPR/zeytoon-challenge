"""Pure intent-pattern application over a collapsed plan set."""

from __future__ import annotations


class ExplainService:
    """Applies caller-supplied predicates and thresholds to ranked interests."""

    @staticmethod
    def explain(ranked_interests, patterns, thresholds) -> dict:
        collapsed = {}
        for interest in ranked_interests or []:
            plans = (
                interest.get("plans", [])
                if isinstance(interest, dict)
                else getattr(interest, "plans", [])
            )
            for plan in plans or []:
                collapsed.setdefault(_plan_id(plan), plan)
        if not collapsed:
            return {}

        plans = list(collapsed.values())
        result = {}
        for name, predicate in patterns or []:
            matches = [plan for plan in plans if predicate(plan)]
            minimum = thresholds.get(name, 0)
            if len(matches) >= minimum:
                result[name] = sorted(matches, key=_plan_id)
        return result


def _plan_id(plan):
    if isinstance(plan, dict):
        return plan["plan_id"]
    return plan.plan_id


__all__ = ["ExplainService"]
