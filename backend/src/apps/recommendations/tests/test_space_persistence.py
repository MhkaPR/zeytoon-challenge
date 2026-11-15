"""Persistence of the recommendation space (PostgreSQL source of truth)."""

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.recommendations.models import RecommendationSpace
from apps.recommendations.services.v1.store import PlanSpaceProvider, SPACE_KEY
from apps.recommendations.tests.factories import catalog


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def _records(record_list):
    return [
        {"id": record.pk, "values": record.values, "published_at": record.published_at}
        for record in record_list
    ]


@pytest.mark.django_db
def test_space_is_persisted_and_survives_cache_flush():
    records = catalog(
        {"price_amount": 10, "plan_name": "سرور گیمینگ"},
        {"price_amount": 30, "plan_name": "هاست ایمیل"},
    )
    provider = PlanSpaceProvider()
    first = provider.load(_records(records))
    assert RecommendationSpace.objects.filter(is_active=True).count() == 1

    cache.clear()
    second = provider.load(_records(records))

    assert second["version"] == first["version"]
    assert second["ids"] == first["ids"]
    # No refit: the persisted row is served directly.
    assert RecommendationSpace.objects.filter(is_active=True).count() == 1


@pytest.mark.django_db
def test_refresh_activates_new_version_and_invalidates_cache():
    records = catalog({"price_amount": 10, "plan_name": "plan one"})
    provider = PlanSpaceProvider()
    provider.refresh(_records(records))
    first_active = RecommendationSpace.objects.get(is_active=True)

    records[0].values = {"price_amount": 99, "plan_name": "plan two"}
    records[0].save(update_fields=["values"])
    provider.refresh(_records(records))

    active = RecommendationSpace.objects.filter(is_active=True)
    assert active.count() == 1
    assert active.first().version != first_active.version
    assert RecommendationSpace.objects.filter(is_active=True).first().pk != first_active.pk


@pytest.mark.django_db
def test_failed_rebuild_keeps_previous_active_row(monkeypatch):
    records = catalog({"price_amount": 10, "plan_name": "plan one"})
    provider = PlanSpaceProvider()
    provider.refresh(_records(records))
    active_before = RecommendationSpace.objects.get(is_active=True)

    def boom(*args, **kwargs):
        raise ValueError("cannot fit a recommendation space without plans")

    monkeypatch.setattr(provider, "_build", boom)
    with pytest.raises(ValueError):
        provider.refresh(_records(records))

    active_after = RecommendationSpace.objects.get(is_active=True)
    assert active_after.pk == active_before.pk


@pytest.mark.django_db
def test_datetime_published_at_is_persisted_as_iso_string():
    records = catalog({"price_amount": 10, "plan_name": "plan"})
    records[0].published_at = timezone.now()
    records[0].save(update_fields=["published_at"])

    bundle = PlanSpaceProvider().refresh(_records(records))

    row = RecommendationSpace.objects.get(is_active=True)
    assert all(isinstance(value, str) for value in row.published_at)
    assert row.published_at == [
        value.isoformat() if hasattr(value, "isoformat") else value
        for value in bundle["published_at"]
    ]
