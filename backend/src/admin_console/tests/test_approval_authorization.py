"""US1 — operator-only authorization on the approval surface (FR-001, FR-005)."""

import pytest

pytestmark = pytest.mark.django_db


def test_guest_is_refused(api_client, company):
    response = api_client.get("/api/v1/ops/approvals")
    assert response.status_code == 401


def test_regular_user_is_refused(auth_client, company):
    response = auth_client.get("/api/v1/ops/approvals")
    assert response.status_code == 403


def test_operator_is_allowed(operator_client, company):
    response = operator_client.get("/api/v1/ops/approvals")
    assert response.status_code == 200


def test_regular_user_cannot_record_a_decision(auth_client, company):
    response = auth_client.post(
        f"/api/v1/ops/companies/{company.pk}/verification-decisions",
        {"outcome": "approved"},
        format="json",
    )
    assert response.status_code == 403
