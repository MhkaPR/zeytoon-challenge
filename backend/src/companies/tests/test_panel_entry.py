"""Contract tests for panel entry/switching (US2, FR-023..FR-027, SC-003)."""

import pytest

from companies.services import record_verification_decision, register_company

pytestmark = pytest.mark.django_db


def _register(owner, domain="example.com"):
    return register_company(
        owner,
        {
            "domain": domain,
            "company_name": "Example Hosting",
            "representative_name": "Ali Rezaei",
            "phone_number": "02123456789",
        },
    )


def test_switcher_empty_state(auth_client):
    response = auth_client.get("/api/v1/companies/panel-switcher")
    assert response.status_code == 200
    body = response.json()
    assert body["empty_state"] is True
    assert body["companies"] == []
    assert body["message"]


def test_panel_entry_full_panel_for_verified(auth_client, owner, operator):
    company = _register(owner)
    record_verification_decision(company, operator, "approved")
    response = auth_client.get(f"/api/v1/companies/{company.pk}/panel-entry")
    assert response.status_code == 200
    assert response.json()["view"] == "full_panel"


def test_panel_entry_continue_view_for_pending(auth_client, owner):
    company = _register(owner)
    response = auth_client.get(f"/api/v1/companies/{company.pk}/panel-entry")
    assert response.status_code == 200
    body = response.json()
    assert body["view"] == "continue_registration"
    assert body["verification_status"] == "pending"
    assert body["current_step"] == "verification"
    assert body["step_progress"]


def test_direct_full_panel_redirects_when_unverified(auth_client, owner):
    company = _register(owner)
    response = auth_client.get(f"/api/v1/companies/{company.pk}/panel")
    assert response.status_code == 303
    assert response["Location"] == f"/api/v1/companies/{company.pk}/panel-entry"


def test_full_panel_renders_when_verified(auth_client, owner, operator):
    company = _register(owner)
    record_verification_decision(company, operator, "approved")
    response = auth_client.get(f"/api/v1/companies/{company.pk}/panel")
    assert response.status_code == 200
    body = response.json()
    assert body["company"]["verification_status"] == "verified"
    assert "plan_eligibility" in body
