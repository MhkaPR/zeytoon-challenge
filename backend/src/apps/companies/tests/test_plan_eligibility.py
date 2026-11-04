"""Plan-eligibility gate tests (US4, FR-030, FR-031, SC-002)."""

import pytest

from companies.models import Company
from companies.services import can_manage_plans, register_company

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


def test_unverified_and_uncharged_names_both(owner):
    company = _register(owner)
    result = can_manage_plans(company)
    assert result["allowed"] is False
    assert set(result["missing"]) == {"verified", "charged"}
    assert result["message"]


def test_verified_but_uncharged_names_charge(owner):
    company = _register(owner)
    company.verification_status = Company.VerificationStatus.VERIFIED
    company.save(update_fields=["verification_status"])
    result = can_manage_plans(company)
    assert result["allowed"] is False
    assert result["missing"] == ["charged"]


def test_charged_but_unverified_names_verified(owner):
    company = _register(owner)
    company.charge_status = Company.ChargeStatus.CHARGED
    company.save(update_fields=["charge_status"])
    result = can_manage_plans(company)
    assert result["missing"] == ["verified"]


def test_verified_and_charged_is_allowed(owner):
    company = _register(owner)
    company.verification_status = Company.VerificationStatus.VERIFIED
    company.charge_status = Company.ChargeStatus.CHARGED
    company.save(update_fields=["verification_status", "charge_status"])
    result = can_manage_plans(company)
    assert result["allowed"] is True
    assert result["missing"] == []


def test_gate_endpoint(auth_client, owner):
    company = _register(owner)
    response = auth_client.get(f"/api/v1/companies/{company.pk}/plan-eligibility")
    assert response.status_code == 200
    assert response.json()["allowed"] is False
