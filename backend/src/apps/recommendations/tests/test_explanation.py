from types import SimpleNamespace

import numpy as np

from apps.recommendations import conf
from apps.recommendations.services.v1.explanation import IntentExplainer
from apps.recommendations.services.v1.intent_scoring import IntentScore


NAMES = ["price", "has_cpu", "cpu", "has_ram", "ram", "has_disk", "disk"]


def _bundle():
    values = []
    masks = []
    ids = []
    for index in range(60):
        if index < 20:
            row = [0.2, 1.0, 0.8, 1.0, 0.8, 1.0, 0.8]
        elif index < 40:
            row = [0.2, 1.0, 0.1, 1.0, 0.1, 1.0, 0.1]
        else:
            row = [0.8, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2]
        values.append(row)
        masks.append([1.0] * len(NAMES))
        ids.append(index + 1)
    return {
        "values": np.asarray(values, dtype=float),
        "masks": np.asarray(masks, dtype=float),
        "ids": ids,
        "published_at": [""] * len(ids),
        "space": SimpleNamespace(names=NAMES),
    }


def _value_position():
    return [0.2, 1.0, 0.8, 1.0, 0.8, 1.0, 0.8]


def _clusters(*positions):
    return SimpleNamespace(
        states=[SimpleNamespace(x=list(position)) for position in positions]
    )


def _allow_all(monkeypatch):
    monkeypatch.setattr(conf, "explain_min_pattern_size", lambda: 0)
    monkeypatch.setattr(conf, "explain_alpha", lambda: 1.0)
    monkeypatch.setattr(conf, "explain_min_lift", lambda: 0.0)
    monkeypatch.setattr(conf, "explain_min_mcc", lambda: 0.0)
    monkeypatch.setattr(conf, "explain_k", lambda: 20)
    monkeypatch.setattr(conf, "explain_negative_enabled", lambda: True)


def test_each_cluster_gets_its_own_explanation(monkeypatch):
    _allow_all(monkeypatch)
    monkeypatch.setattr(IntentExplainer, "_aligns", lambda self, key, rows: True)

    explanations = IntentExplainer(_bundle()).explain_all(
        _clusters(_value_position(), _value_position())
    )

    assert len(explanations) == 2
    assert [item["cluster_id"] for item in explanations] == [0, 1]
    assert [item["intent"] for item in explanations] == ["value", "value"]
    assert all(item["message"].endswith("؟") for item in explanations)


def test_no_qualifying_pattern_returns_exploring(monkeypatch):
    _allow_all(monkeypatch)
    monkeypatch.setattr(IntentExplainer, "_aligns", lambda self, key, rows: False)

    explanation = IntentExplainer(_bundle()).explain_cluster(
        _value_position(), 0, []
    )

    assert explanation["intent"] == "exploring"
    assert explanation["direction"] is None
    assert explanation["confidence"] is None
    assert explanation["message"].endswith("؟")


def test_negative_intents_are_rejected_when_flag_is_disabled(monkeypatch):
    _allow_all(monkeypatch)
    monkeypatch.setattr(conf, "explain_negative_enabled", lambda: False)
    monkeypatch.setattr(IntentExplainer, "_aligns", lambda self, key, rows: True)
    negative = IntentScore("cheap", 3.0, 0.01, -0.5, 1.5, "negative")
    monkeypatch.setattr(
        "apps.recommendations.services.v1.explanation.evaluate_patterns",
        lambda *args, **kwargs: [negative],
    )

    explanation = IntentExplainer(_bundle()).explain_cluster(
        _value_position(), 0, []
    )

    assert explanation["intent"] == "exploring"


def test_corroboration_requires_minimum_clicks(monkeypatch):
    _allow_all(monkeypatch)
    monkeypatch.setattr(conf, "explain_min_clicks", lambda: 3)
    explainer = IntentExplainer(_bundle())

    assert explainer._aligns("cheap", []) is False
    assert explainer._aligns("cheap", [0, 1]) is False
    assert explainer._aligns("cheap", [0, 1, 2]) is True
