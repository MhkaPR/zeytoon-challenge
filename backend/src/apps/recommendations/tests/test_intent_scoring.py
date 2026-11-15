from apps.recommendations import conf
from apps.recommendations.services.v1.intent_scoring import (
    ContingencyTable,
    IntentScore,
    best_score,
    contingency_table,
    evaluate_pattern,
    evaluate_patterns,
    fisher_p_value,
    lift,
    matthews_correlation,
)


def test_contingency_table_counts():
    table = contingency_table({0, 1, 2}, {1, 2, 3, 4}, 10)
    assert (table.tp, table.fp, table.fn, table.tn) == (2, 2, 1, 5)


def test_lift_and_mcc_direction():
    table = ContingencyTable(tp=20, fp=0, fn=0, tn=20)
    assert lift(table) == 2.0
    assert matthews_correlation(20, 20, 0, 0) == 1.0
    assert matthews_correlation(0, 0, 20, 20) == -1.0


def test_zero_denominator_mcc_is_zero():
    assert matthews_correlation(0, 0, 0, 0) == 0.0


def test_gate_one_rejects_small_patterns(monkeypatch):
    monkeypatch.setattr(conf, "explain_min_pattern_size", lambda: 30)
    table = ContingencyTable(tp=10, fp=19, fn=10, tn=100)
    assert evaluate_pattern("cheap", table) is None


def test_gate_two_rejects_insignificant_patterns(monkeypatch):
    monkeypatch.setattr(conf, "explain_min_pattern_size", lambda: 0)
    monkeypatch.setattr(conf, "explain_alpha", lambda: 0.0)
    table = ContingencyTable(tp=20, fp=0, fn=0, tn=20)
    assert evaluate_pattern("cheap", table) is None


def test_gate_three_rejects_weak_lift(monkeypatch):
    monkeypatch.setattr(conf, "explain_min_pattern_size", lambda: 0)
    monkeypatch.setattr(conf, "explain_alpha", lambda: 1.0)
    monkeypatch.setattr(conf, "explain_min_lift", lambda: 99.0)
    table = ContingencyTable(tp=20, fp=0, fn=0, tn=20)
    assert evaluate_pattern("cheap", table) is None


def test_mcc_filter_rejects_directionless_patterns(monkeypatch):
    monkeypatch.setattr(conf, "explain_min_pattern_size", lambda: 0)
    monkeypatch.setattr(conf, "explain_alpha", lambda: 1.0)
    monkeypatch.setattr(conf, "explain_min_lift", lambda: 0.0)
    monkeypatch.setattr(conf, "explain_min_mcc", lambda: 0.99)
    table = ContingencyTable(tp=15, fp=5, fn=5, tn=15)
    assert evaluate_pattern("cheap", table) is None


def test_negative_mcc_produces_negative_direction(monkeypatch):
    monkeypatch.setattr(conf, "explain_min_pattern_size", lambda: 0)
    monkeypatch.setattr(conf, "explain_alpha", lambda: 1.0)
    monkeypatch.setattr(conf, "explain_min_lift", lambda: 0.0)
    monkeypatch.setattr(conf, "explain_min_mcc", lambda: 0.0)
    score = evaluate_pattern(
        "cheap", ContingencyTable(tp=0, fp=20, fn=20, tn=0)
    )
    assert score is not None
    assert score.direction == "negative"


def test_exploring_is_never_scored():
    scores = evaluate_patterns(
        {0, 1},
        {"cheap": {0, 1}, "exploring": {0, 1}},
        10,
    )
    assert all(score.key != "exploring" for score in scores)


def test_best_score_ranks_by_lift_times_abs_mcc():
    low = IntentScore("cheap", 2.0, 0.01, 0.2, 0.4, "positive")
    high = IntentScore("value", 3.0, 0.01, 0.5, 1.5, "positive")
    assert best_score([low, high]) is high
