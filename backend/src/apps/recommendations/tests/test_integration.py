import uuid
from types import SimpleNamespace

import numpy as np
import pytest

from apps.accounts.models import User
from apps.catalog.interfaces import CatalogInterface
from apps.recommendations import conf
from apps.recommendations.services.v1.explain import ExplainService
from apps.recommendations.services.v1.intent_patterns import (
    INTENT_PATTERNS,
    REAL_PATTERN_KEYS,
    build_intent_features,
)
from apps.recommendations.services.v1.rank import RankService
from apps.recommendations.services.v1.ranking import RankingService
from apps.recommendations.services.v1.record import Interaction, RecordService
from apps.recommendations.services.v1.signals import SignalRecorder
from apps.recommendations.tests.factories import catalog

NAMES = ["price", "has_cpu", "cpu", "has_ram", "ram", "has_disk", "disk"]


class StaticProvider:
    def __init__(self, bundle):
        self.bundle = bundle

    def load(self, records):
        return self.bundle


def _row(price, spec):
    return [price, 1.0, spec, 1.0, spec, 1.0, spec]


def _bundle():
    values = [_row(0.1, 0.1) for _ in range(10)]
    values += [_row(0.9, 0.9) for _ in range(10)]
    return {
        "values": np.asarray(values, dtype=float),
        "masks": np.ones((20, len(NAMES))),
        "ids": list(range(1, 21)),
        "published_at": [""] * 20,
        "space": SimpleNamespace(names=NAMES),
    }


def _patterns():
    return [
        (
            key,
            lambda ref, key=key: INTENT_PATTERNS[key].matches(ref.features),
        )
        for key in REAL_PATTERN_KEYS
    ]


def _attach_features(ranked, bundle):
    features = build_intent_features(bundle)
    by_id = dict(zip(bundle["ids"], features))
    for interest in ranked:
        for ref in interest.plans:
            ref.features = by_id[ref.plan_id]
    return ranked


def _user(name):
    suffix = sum(ord(char) for char in name) % 10_000_000
    return User.objects.create_user(
        username=name, password="secret", phone_number=f"0912{suffix:07d}"
    )


@pytest.mark.django_db
def test_full_record_rank_explain_path_surfaces_expected_intent():
    bundle = _bundle()
    provider = StaticProvider(bundle)
    user = _user("integration")

    RecordService().record(
        user.pk,
        Interaction(
            vector=_row(0.1, 0.1),
            weight=0.3,
            kind="destination_visit",
            mask=[1.0] * len(NAMES),
        ),
    )

    ranked = RankService().rank(user.pk, provider, [], 0.35)
    _attach_features(ranked, bundle)
    result = ExplainService.explain(
        ranked,
        _patterns(),
        {"cheap": 5, "value": 5, "spec_heavy": 5, "premium": 5},
    )

    assert set(result) == {"cheap"}
    assert [plan.plan_id for plan in result["cheap"]] == list(range(1, 11))


@pytest.mark.django_db
def test_cold_start_rank_and_explain_are_empty():
    bundle = _bundle()
    user = _user("coldstart")

    ranked = RankService().rank(user.pk, StaticProvider(bundle), [], 0.35)

    assert ranked == []
    assert ExplainService.explain(ranked, _patterns(), {"cheap": 1}) == {}


@pytest.mark.django_db
def test_full_path_is_deterministic():
    bundle = _bundle()
    provider = StaticProvider(bundle)
    user = _user("deterministic")
    RecordService().record(
        user.pk,
        Interaction(
            vector=_row(0.1, 0.1),
            weight=0.3,
            kind="destination_visit",
            mask=[1.0] * len(NAMES),
        ),
    )

    first = _attach_features(RankService().rank(user.pk, provider, [], 0.35), bundle)
    second = _attach_features(RankService().rank(user.pk, provider, [], 0.35), bundle)
    thresholds = {"cheap": 5, "value": 5, "spec_heavy": 5, "premium": 5}
    first_result = ExplainService.explain(first, _patterns(), thresholds)
    second_result = ExplainService.explain(second, _patterns(), thresholds)

    assert [[plan.plan_id for plan in interest.plans] for interest in first] == [
        [plan.plan_id for plan in interest.plans] for interest in second
    ]
    assert list(first_result) == list(second_result)
    assert [p.plan_id for p in first_result["cheap"]] == [
        p.plan_id for p in second_result["cheap"]
    ]


@pytest.mark.django_db
def test_suggested_path_honors_pattern_thresholds(monkeypatch):
    records = catalog(
        *[
            {
                "price_amount": 10 + index if index < 5 else 100 * (index - 4),
                "cpu": index + 1,
                "ram": index + 1,
                "disk": index + 1,
                "plan_name": f"cheap {index}",
            }
            for index in range(20)
        ]
    )
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    for record in records[:5]:
        SignalRecorder().record(
            plan_records,
            "destination_visit",
            [record.pk],
            visitor_id=visitor,
        )
    monkeypatch.setattr(
        conf,
        "pattern_thresholds",
        lambda: {"cheap": 4, "value": 4, "spec_heavy": 4, "premium": 4},
    )

    result = RankingService().suggest_with_explanations(
        plan_records, visitor_id=visitor, limit=10
    )

    assert "cheap" in [item["intent"] for item in result["explanations"]]
