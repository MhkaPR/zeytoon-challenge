"""US6 — classification endpoint contract (FR-023..FR-025)."""

import pytest

from apps.pipeline.models import Link, TableClassification

pytestmark = pytest.mark.django_db


def test_classification_endpoint_returns_verdicts(operator_client, extracted_link):
    response = operator_client.post(
        f"/api/v1/ops/links/{extracted_link.pk}/classifications", {}, format="json"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["classifications"][0]["is_price_table"] is True
    assert body["link"]["pipeline_stage"] == Link.PipelineStage.EXTRACTED


def test_classification_without_tables_is_refused(operator_client, traced_link):
    response = operator_client.post(
        f"/api/v1/ops/links/{traced_link.pk}/classifications", {}, format="json"
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "no_tables_found"


def test_classification_is_idempotent(operator_client, extracted_link):
    endpoint = f"/api/v1/ops/links/{extracted_link.pk}/classifications"
    operator_client.post(endpoint, {}, format="json")
    operator_client.post(endpoint, {}, format="json")

    assert TableClassification.objects.filter(table__link=extracted_link).count() == 1
