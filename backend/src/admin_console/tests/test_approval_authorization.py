"""Operator-only + append-only contract (US1, FR-005, FR-006, SC-001, SC-004)."""

import pytest

from admin_console.models import Site
from companies.models import Company, VerificationDecision

pytestmark = pytest.mark.django_db


def test_owner_cannot_record_a_decision(auth_client, company):
    response = auth_client.post(
        f"/api/v1/ops/companies/{company.pk}/verification-decisions",
        {"outcome": "approved"},
        format="json",
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "admin_required"
    company.refresh_from_db()
    assert company.verification_status == Company.VerificationStatus.PENDING
    assert not VerificationDecision.objects.filter(company=company).exists()
    assert not Site.objects.filter(company=company).exists()


def test_owner_cannot_read_the_queue(auth_client):
    response = auth_client.get("/api/v1/ops/approvals")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "admin_required"


def test_second_decision_leaves_first_record_unchanged(operator_client, company):
    operator_client.post(
        f"/api/v1/ops/companies/{company.pk}/verification-decisions",
        {"outcome": "not_approved", "note": "one"},
        format="json",
    )
    first = VerificationDecision.objects.get(company=company)
    operator_client.post(
        f"/api/v1/ops/companies/{company.pk}/verification-decisions",
        {"outcome": "approved", "note": "two"},
        format="json",
    )
    first.refresh_from_db()
    assert first.outcome == "not_approved"
    assert first.note == "one"
    assert VerificationDecision.objects.filter(company=company).count() == 2


def test_unauthenticated_request_gets_401(api_client, company):
    response = api_client.get("/api/v1/ops/approvals")
    assert response.status_code == 401
