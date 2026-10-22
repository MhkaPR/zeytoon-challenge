"""Verification decision + append-only history tests (US3, FR-013..FR-020, SC-004)."""

import pytest
from django.utils import timezone

from companies.models import Company, CompanyStepProgress, VerificationDecision
from companies.services import record_verification_decision, register_company

pytestmark = pytest.mark.django_db


def _register(owner):
    return register_company(
        owner,
        {
            "domain": "example.com",
            "company_name": "Example Hosting",
            "representative_name": "Ali Rezaei",
            "phone_number": "02123456789",
        },
    )


def test_approval_verifies_company_and_appends_one_entry(company, operator):
    record_verification_decision(company, operator, "approved", note="called")
    company.refresh_from_db()
    assert company.verification_status == Company.VerificationStatus.VERIFIED
    assert VerificationDecision.objects.filter(company=company).count() == 1


def test_not_approved_reopens_step_one(company, operator):
    record_verification_decision(company, operator, "not_approved")
    company.refresh_from_db()
    assert company.verification_status == Company.VerificationStatus.REJECTED
    step_one = CompanyStepProgress.objects.get(
        company=company, step_key="company_information"
    )
    verification = CompanyStepProgress.objects.get(
        company=company, step_key="verification"
    )
    assert step_one.state == CompanyStepProgress.State.OPEN
    assert verification.state == CompanyStepProgress.State.LOCKED


def test_invalid_outcome_is_rejected(company, operator):
    from accounts.exceptions import ApiError

    with pytest.raises(ApiError) as exc:
        record_verification_decision(company, operator, "maybe")
    assert exc.value.code == "invalid_outcome"


def test_history_entries_are_immutable(company, operator):
    decision = record_verification_decision(company, operator, "approved")
    decision.note = "tampered"
    with pytest.raises(ValueError):
        decision.save()
    with pytest.raises(ValueError):
        decision.delete()


def test_later_decision_leaves_earlier_entries(company, operator):
    first = record_verification_decision(company, operator, "not_approved", note="one")
    record_verification_decision(company, operator, "approved", note="two")
    company.refresh_from_db()
    assert company.verification_status == Company.VerificationStatus.VERIFIED
    first.refresh_from_db()
    assert first.outcome == "not_approved"
    assert first.note == "one"
    assert VerificationDecision.objects.filter(company=company).count() == 2


def test_contract_decision_endpoint(api_client, company, operator):
    from rest_framework_simplejwt.tokens import RefreshToken

    token = str(RefreshToken.for_user(operator).access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.post(
        f"/api/v1/companies/{company.pk}/verification-decisions",
        {"outcome": "approved", "note": "ok"},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["verification_status"] == "verified"


def test_owner_cannot_decide_their_own_verification(auth_client, company, owner):
    response = auth_client.post(
        f"/api/v1/companies/{company.pk}/verification-decisions",
        {"outcome": "approved"},
        format="json",
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_permitted"


def test_invalid_outcome_via_endpoint(api_client, company, operator):
    from rest_framework_simplejwt.tokens import RefreshToken

    token = str(RefreshToken.for_user(operator).access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.post(
        f"/api/v1/companies/{company.pk}/verification-decisions",
        {"outcome": "maybe"},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_field"
