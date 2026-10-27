"""Approval queue contract tests (US1, FR-001..FR-004, SC-002, SC-003)."""

import pytest

from admin_console.models import Site
from companies.models import Company, CompanyStepProgress, VerificationDecision

pytestmark = pytest.mark.django_db


def test_queue_lists_pending_company_with_masked_phone(operator_client, company, owner):
    from companies import services as company_services

    company_services.register_company(
        owner,
        {
            "domain": "example.com",
            "company_name": "Duplicate Hosting",
            "representative_name": "Sara",
            "phone_number": "02199999999",
        },
    )
    response = operator_client.get("/api/v1/ops/approvals")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    row = next(r for r in body["results"] if r["company_id"] == company.pk)
    assert row["company_name"] == "Example Hosting"
    assert row["representative_name"] == "Ali Rezaei"
    assert row["domain"] == "example.com"
    assert "021" in row["phone_masked"] and "***" in row["phone_masked"]
    assert row["duplicate_domain_warning"] is True
    assert company.pk not in row["duplicate_of"]


def test_approved_verifies_creates_site_in_onboarding(operator_client, company):
    response = operator_client.post(
        f"/api/v1/ops/companies/{company.pk}/verification-decisions",
        {"outcome": "approved", "note": "checked"},
        format="json",
    )
    assert response.status_code == 201
    company.refresh_from_db()
    assert company.verification_status == Company.VerificationStatus.VERIFIED
    assert VerificationDecision.objects.filter(company=company).count() == 1
    site = Site.objects.get(company=company)
    assert site.maintenance_state == Site.MaintenanceState.ONBOARDING
    assert response.json()["company"]["verified"] is True


def test_not_approved_reopens_step_one_and_suspends_site(operator_client, company):
    operator_client.post(
        f"/api/v1/ops/companies/{company.pk}/verification-decisions",
        {"outcome": "approved"},
        format="json",
    )
    response = operator_client.post(
        f"/api/v1/ops/companies/{company.pk}/verification-decisions",
        {"outcome": "not_approved", "note": "unclear docs"},
        format="json",
    )
    assert response.status_code == 201
    company.refresh_from_db()
    assert company.verification_status == Company.VerificationStatus.REJECTED
    step_one = CompanyStepProgress.objects.get(
        company=company, step_key="company_information"
    )
    assert step_one.state == CompanyStepProgress.State.OPEN
    site = Site.objects.get(company=company)
    assert site.maintenance_state == Site.MaintenanceState.SUSPENDED


def test_unknown_outcome_is_rejected(operator_client, company):
    response = operator_client.post(
        f"/api/v1/ops/companies/{company.pk}/verification-decisions",
        {"outcome": "maybe"},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_field"
