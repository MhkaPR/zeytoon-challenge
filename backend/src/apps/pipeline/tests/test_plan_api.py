"""US7 — plan extraction endpoints (FR-026..FR-031)."""

import pytest

from apps.pipeline.services.v1 import pipeline as services
from apps.pipeline.models import Link, PlanRecord
from apps.pipeline.tests.conftest import HOSTING_PLAN_VALUES

pytestmark = pytest.mark.django_db


def test_plan_endpoint_extracts_and_lists(operator_client, labeled_link, stub_llm):
    stub_llm.classifications = [
        {
            "table_index": 0,
            "is_correct": True,
            "plan_type": "hosting",
            "confidence": 1.0,
        }
    ]
    stub_llm.plans = [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 1.0}]

    response = operator_client.post(f"/api/v1/ops/links/{labeled_link.pk}/plans")

    assert response.status_code == 201
    body = response.json()
    assert body["plans"][0]["values"]["plan_name"] == "Starter"
    assert body["link"]["pipeline_stage"] == Link.PipelineStage.PLANS_EXTRACTED

    listed = operator_client.get(f"/api/v1/ops/links/{labeled_link.pk}/plans")
    assert listed.json()["plans"][0]["plan_type"] == "hosting"


def test_plan_endpoint_requires_a_plans_table(operator_client, labeled_link):
    table = labeled_link.extracted_tables.get()
    table.rows.all().delete()
    table.rows.create(row_index=0, cells={"col-0": "About", "col-1": "us"})
    table.rows.create(row_index=1, cells={"col-0": "Contact", "col-1": "team"})
    services.classify_and_extract_link_tables(labeled_link)

    response = operator_client.post(f"/api/v1/ops/links/{labeled_link.pk}/plans")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "plans_required"
    assert PlanRecord.objects.count() == 0


def test_plan_schema_endpoint_exposes_fields(operator_client):
    response = operator_client.get("/api/v1/ops/plan-schema?plan_type=hosting")
    assert response.status_code == 200
    field_keys = {field["key"] for field in response.json()["fields"]}
    assert {"plan_name", "price_amount"} <= field_keys


def test_operator_can_toggle_a_plan_exclusion(operator_client, planned_link):
    plan = PlanRecord.objects.get(link=planned_link)
    endpoint = f"/api/v1/ops/links/{planned_link.pk}/plans/{plan.pk}/ignore"

    ignored = operator_client.put(endpoint, {"ignored": True}, format="json")

    assert ignored.status_code == 200
    assert ignored.json()["ignored"] is True
    listed = operator_client.get(f"/api/v1/ops/links/{planned_link.pk}/plans")
    assert listed.json()["plans"][0]["ignored"] is True

    restored = operator_client.put(endpoint, {"ignored": False}, format="json")
    assert restored.status_code == 200
    assert restored.json()["ignored"] is False
