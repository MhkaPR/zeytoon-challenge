import pytest
from django.core.cache import cache

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
