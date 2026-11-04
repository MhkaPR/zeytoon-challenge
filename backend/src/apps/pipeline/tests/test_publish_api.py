"""US9 — publish endpoint contract (FR-036..FR-038)."""

import pytest

from apps.pipeline.tests.conftest import HOSTING_PLAN_VALUES
from apps.catalog.models import PublishedRecord

pytestmark = pytest.mark.django_db


def test_publish_endpoint_publishes_plan_records(
    operator_client, planned_link, stub_llm
):
    stub_llm.plans = [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 1.0}]
    operator_client.post(f"/api/v1/ops/links/{planned_link.pk}/plans")

    response = operator_client.post(f"/api/v1/ops/links/{planned_link.pk}/publish")

    assert response.status_code == 200
    assert response.json()["published"] == 1
    assert PublishedRecord.objects.filter(is_published=True).count() == 1


def test_publish_endpoint_requires_plans(operator_client, kept_link):
    response = operator_client.post(f"/api/v1/ops/links/{kept_link.pk}/publish")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "plans_required"
