from types import SimpleNamespace

from apps.recommendations.services.v1.explain import ExplainService
from apps.recommendations.services.v1.rank import RankService


def _plan(plan_id, cheap=False):
    return SimpleNamespace(plan_id=plan_id, cheap=cheap)


def _interest(node_id, plans):
    return SimpleNamespace(node_id=node_id, plans=plans)


def test_empty_ranked_interests_returns_empty_dict():
    assert (
        ExplainService.explain([], [("cheap", lambda plan: plan.cheap)], {"cheap": 1})
        == {}
    )


def test_deduplicates_plans_across_nodes():
    shared = _plan(1, cheap=True)
    ranked = [
        _interest("a", [shared, _plan(2, cheap=True)]),
        _interest("b", [shared]),
    ]

    result = ExplainService.explain(
        ranked, [("cheap", lambda plan: plan.cheap)], {"cheap": 2}
    )

    assert [plan.plan_id for plan in result["cheap"]] == [1, 2]


def test_pattern_below_threshold_is_omitted():
    ranked = [_interest("a", [_plan(1, cheap=True)])]

    result = ExplainService.explain(
        ranked, [("cheap", lambda plan: plan.cheap)], {"cheap": 2}
    )

    assert result == {}


def test_pattern_at_threshold_is_present_with_full_matches():
    ranked = [
        _interest("a", [_plan(3, cheap=True), _plan(1, cheap=True)]),
    ]

    result = ExplainService.explain(
        ranked, [("cheap", lambda plan: plan.cheap)], {"cheap": 2}
    )

    assert [plan.plan_id for plan in result["cheap"]] == [1, 3]


def test_output_order_is_deterministic():
    ranked = [_interest("a", [_plan(5), _plan(2), _plan(9)])]

    result = ExplainService.explain(ranked, [("all", lambda plan: True)], {"all": 1})

    assert [plan.plan_id for plan in result["all"]] == [2, 5, 9]


def test_explain_does_not_call_rank(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("explain must not call rank")

    monkeypatch.setattr(RankService, "rank", _boom)
    ranked = [_interest("a", [_plan(1, cheap=True)])]

    result = ExplainService.explain(
        ranked, [("cheap", lambda plan: plan.cheap)], {"cheap": 1}
    )

    assert "cheap" in result
