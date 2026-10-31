"""US7 — plan extraction endpoints (FR-026..FR-031)."""

import pytest

from admin_console.models import Link, PlanRecord
from admin_console.tests.conftest import HOSTING_PLAN_VALUES

pytestmark = pytest.mark.django_db


def test_plan_endpoint_extracts_and_lists(operator_client, classified_link, stub_llm):
    stub_llm.plans = [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 0.85}]

    response = operator_client.post(f"/api/v1/ops/links/{classified_link.pk}/plans")

    assert response.status_code == 201
    body = response.json()
    assert body["plans"][0]["values"]["plan_name"] == "Starter"
    assert body["link"]["pipeline_stage"] == Link.PipelineStage.PLANS_EXTRACTED

    listed = operator_client.get(f"/api/v1/ops/links/{classified_link.pk}/plans")
    assert listed.json()["plans"][0]["plan_type"] == "hosting"


def test_plan_endpoint_requires_a_plans_table(operator_client, extracted_link, stub_llm):
    stub_llm.classifications = [
        {"table_index": 0, "is_plans_table": False, "plan_type": "", "confidence": 0.9}
    ]
    operator_client.post(f"/api/v1/ops/links/{extracted_link.pk}/classifications",
                         {}, format="json")

    response = operator_client.post(f"/api/v1/ops/links/{extracted_link.pk}/plans")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "plans_required"
    assert PlanRecord.objects.count() == 0


def test_plan_schema_endpoint_exposes_fields(operator_client):
    response = operator_client.get("/api/v1/ops/plan-schema?plan_type=hosting")
    assert response.status_code == 200
    field_keys = {field["key"] for field in response.json()["fields"]}
    assert {"plan_name", "price_amount"} <= field_keys
