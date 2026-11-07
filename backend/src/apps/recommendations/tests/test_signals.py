import uuid

import pytest

from apps.recommendations.models import InterestProfile, InterestSignal
from apps.recommendations.services.v1.signals import SignalRecorder
from apps.recommendations.tests.factories import catalog


@pytest.mark.django_db
def test_search_impression_records_one_combined_signal():
    records = catalog(
        {"price_amount": 10, "ram_amount": 1},
        {"price_amount": 20, "ram_amount": 2},
    )
    visitor = uuid.uuid4()
    result = SignalRecorder().record(
        [
            {"id": record.pk, "values": record.values, "published_at": record.published_at}
            for record in records
        ],
        InterestSignal.Kind.SEARCH_IMPRESSION,
        [record.pk for record in records],
        query="hosting",
        visitor_id=visitor,
    )
    assert result["accepted"] == 2
    assert InterestSignal.objects.filter(kind="search_impression").count() == 1
    assert InterestProfile.objects.get(visitor_id=visitor).signal_count == 1


@pytest.mark.django_db
def test_unknown_plan_ids_are_ignored():
    records = catalog({"price_amount": 10})
    result = SignalRecorder().record(
        [
            {"id": record.pk, "values": record.values, "published_at": record.published_at}
            for record in records
        ],
        InterestSignal.Kind.DETAILS_VIEW,
        [record.pk for record in records] + [999999],
        visitor_id=uuid.uuid4(),
    )
    assert result["accepted"] == 1
    assert result["ignored"] == 1
