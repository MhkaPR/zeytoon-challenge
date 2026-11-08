import uuid

import numpy as np
import pytest

from apps.catalog.interfaces import CatalogInterface
from apps.recommendations.models import InterestProfile
from apps.recommendations.services.v1.features import PlanFeatureMapper
from apps.recommendations.services.v1.ranking import RankingService
from apps.recommendations.services.v1.recommender import Recommender
from apps.recommendations.services.v1.signals import SignalRecorder
from apps.recommendations.services.v1.space import PlanSpace
from apps.recommendations.services.v1.state import UserState
from apps.recommendations.tests.factories import catalog


def test_semantic_dimensions_shift_order():
    titles = [
        "سرور مجازی گیمینگ",
        "سرور اختصاصی گیمینگ",
        "سرور ماینکرفت",
        "هاستینگ وردپرس سریع",
        "هاستینگ وردپرس حرفه‌ای",
        "سرور ایمیل اختصاصی",
    ]
    features = [
        PlanFeatureMapper().map(
            {"id": index, "values": {"price_amount": 10, "plan_name": title}}
        )
        for index, title in enumerate(titles)
    ]
    space = PlanSpace(n_bins=3).fit(features)
    values, masks = space.transform(features)
    position = space.prior(values, masks)
    state = UserState(position, uncertainty=np.full_like(position, 1.0))
    state.update(values[0], masks[0], noise=0.3)

    distances = Recommender.distances(values, masks, state.x)
    gaming = distances[:3].mean()
    other = distances[3:].mean()
    assert gaming < other


@pytest.mark.django_db
def test_outdated_profile_is_rebuilt():
    records = catalog(
        {"price_amount": 10, "plan_name": "سرور گیمینگ"},
        {"price_amount": 20, "plan_name": "هاست ایمیل"},
    )
    visitor = uuid.uuid4()
    InterestProfile.objects.create(
        visitor_id=visitor,
        position=[0.0],
        uncertainty=[0.1],
        space_version="old",
    )
    plan_records = CatalogInterface.published_plan_records()
    ordered = RankingService().rank(
        plan_records,
        [record.pk for record in records],
        visitor_id=visitor,
    )
    assert sorted(ordered) == sorted(record.pk for record in records)


@pytest.mark.django_db
def test_multiple_themes_are_kept_and_ranked():
    titles = [
        "python10",
        "python20",
        "python30",
        "python40",
        "هاست nodejs 1",
        "هاست nodejs 2",
        "هاست nodejs 3",
        "هاست nodejs 4",
        "Email10",
        "Email20",
        "Email30",
        "Email40",
    ]
    records = catalog(
        *[
            {"price_amount": 10 + index, "plan_name": title}
            for index, title in enumerate(titles)
        ]
    )
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    recorder = SignalRecorder()
    for index in (0, 4, 8):
        recorder.record(
            plan_records,
            "destination_visit",
            [records[index].pk],
            visitor_id=visitor,
        )

    profile = InterestProfile.objects.get(visitor_id=visitor)
    assert len(profile.position) == 3

    ordered = RankingService().rank(
        plan_records,
        [record.pk for record in records],
        visitor_id=visitor,
    )
    by_id = {record.pk: record.values["plan_name"] for record in records}
    top = [by_id[plan_id] for plan_id in ordered[:6]]
    assert any(title.startswith("python") for title in top)
    assert any("nodejs" in title for title in top)
    assert any(title.startswith("Email") for title in top)


@pytest.mark.django_db
def test_suggest_returns_twenty_ranked_plans():
    records = catalog(
        *[
            {"price_amount": 10 + index, "plan_name": f"plan {index}"}
            for index in range(25)
        ]
    )
    plan_records = CatalogInterface.published_plan_records()
    suggested = RankingService().suggest(plan_records, limit=20)
    assert len(suggested) == 20
    assert len(set(suggested)) == 20
    assert set(suggested).issubset({record.pk for record in records})
