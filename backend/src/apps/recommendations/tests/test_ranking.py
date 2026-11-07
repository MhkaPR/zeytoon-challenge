import uuid

import numpy as np
import pytest

from apps.catalog.interfaces import CatalogInterface
from apps.recommendations.models import InterestProfile
from apps.recommendations.services.v1.features import PlanFeatureMapper
from apps.recommendations.services.v1.ranking import RankingService
from apps.recommendations.services.v1.recommender import Recommender
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
