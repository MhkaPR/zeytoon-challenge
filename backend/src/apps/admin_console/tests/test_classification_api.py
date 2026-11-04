"""US6 — classification endpoint contract (FR-023..FR-025)."""

import pytest

from apps.admin_console.models import Link, TableClassification
from apps.admin_console.tests.conftest import HOSTING_PLAN_VALUES

pytestmark = pytest.mark.django_db


def test_classification_endpoint_returns_verdicts(
    operator_client, extracted_link, stub_llm
):
    stub_llm.classifications = [
        {
            "table_index": 0,
            "is_plans_table": True,
            "plan_type": "hosting",
            "confidence": 0.9,
        }
    ]
    stub_llm.plans = [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 1.0}]

    response = operator_client.post(
        f"/api/v1/ops/links/{extracted_link.pk}/classifications", {}, format="json"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["classifications"][0]["is_plans_table"] is True
    assert body["link"]["pipeline_stage"] == Link.PipelineStage.PLANS_EXTRACTED


def test_classification_without_tables_is_refused(operator_client, traced_link):
    response = operator_client.post(
        f"/api/v1/ops/links/{traced_link.pk}/classifications", {}, format="json"
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "no_tables_found"


def test_classification_returns_202_on_budget_exhaustion(
    operator_client, extracted_link, stub_llm
):
    stub_llm.exhausted_stages = {"classification"}

    response = operator_client.post(
        f"/api/v1/ops/links/{extracted_link.pk}/classifications", {}, format="json"
    )

    assert response.status_code == 202
    assert response.json()["error"]["code"] == "awaiting_llm_budget"
    assert TableClassification.objects.count() == 0
