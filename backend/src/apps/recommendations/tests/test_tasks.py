import pytest
from django.core.cache import cache
from django.core.management import call_command

from apps.recommendations.models import InterestProfile
from apps.recommendations.services.v1.signals import SignalRecorder
from apps.recommendations.services.v1.store import PlanSpaceProvider
from apps.recommendations.tasks import refresh_plan_space_task
from apps.recommendations.tests.factories import catalog


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_refresh_writes_cache():
    catalog(
        {"price_amount": 10, "plan_name": "سرور گیمینگ"},
        {"price_amount": 20, "plan_name": "هاست ایمیل"},
    )
    result = refresh_plan_space_task.func()
    assert result["plans"] == 2
    assert result["version"]


@pytest.mark.django_db
def test_failed_refresh_keeps_previous_cache(monkeypatch):
    catalog(
        {"price_amount": 10, "plan_name": "سرور گیمینگ"},
        {"price_amount": 20, "plan_name": "هاست ایمیل"},
    )
    cache.set("previous-space", {"version": "previous"})

    def fail(self, records):
        raise RuntimeError("fit failed")

    monkeypatch.setattr(PlanSpaceProvider, "refresh", fail)
    with pytest.raises(RuntimeError):
        refresh_plan_space_task.func()
    assert cache.get("previous-space") == {"version": "previous"}


@pytest.mark.django_db
def test_rebuild_clusters_from_signals():
    import uuid

    from apps.catalog.interfaces import CatalogInterface

    records = catalog(
        {"price_amount": 10, "plan_name": "python10"},
        {"price_amount": 20, "plan_name": "python20"},
        {"price_amount": 30, "plan_name": "هاست nodejs 1"},
        {"price_amount": 40, "plan_name": "هاست nodejs 2"},
        {"price_amount": 50, "plan_name": "Email10"},
        {"price_amount": 60, "plan_name": "Email20"},
    )
    plan_records = CatalogInterface.published_plan_records()
    visitor = uuid.uuid4()
    recorder = SignalRecorder()
    for index in (0, 2, 4):
        recorder.record(
            plan_records,
            "destination_visit",
            [records[index].pk],
            visitor_id=visitor,
        )
    profile = InterestProfile.objects.get(visitor_id=visitor)
    profile.position = [0.0]
    profile.uncertainty = [1.0]
    profile.space_version = "old"
    profile.save()

    call_command("rebuild_interest_clusters", "--visitor-id", str(visitor))

    profile.refresh_from_db()
    assert len(profile.position) == 3
