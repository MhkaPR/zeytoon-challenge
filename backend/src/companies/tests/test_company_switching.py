"""Company-switching isolation tests (US2, FR-022, FR-029)."""

import pytest

from companies.services import record_verification_decision, register_company

pytestmark = pytest.mark.django_db


def _register(owner, domain, name):
    return register_company(
        owner,
        {
            "domain": domain,
            "company_name": name,
            "representative_name": "Rep",
            "phone_number": "02123456789",
        },
    )


def test_switcher_lists_only_selected_fields_per_company(auth_client, owner, operator):
    pending = _register(owner, "pending.com", "Pending Co")
    verified = _register(owner, "verified.com", "Verified Co")
    record_verification_decision(verified, operator, "approved")

    response = auth_client.get("/api/v1/companies/panel-switcher")
    assert response.status_code == 200
    body = response.json()
    by_id = {c["id"]: c for c in body["companies"]}
    assert by_id[pending.pk]["verification_status"] == "pending"
    assert by_id[pending.pk]["unverified"] is True
    assert by_id[verified.pk]["verification_status"] == "verified"
    assert by_id[verified.pk]["unverified"] is False


def test_entry_payload_reflects_selected_company_only(auth_client, owner, operator):
    pending = _register(owner, "pending.com", "Pending Co")
    verified = _register(owner, "verified.com", "Verified Co")
    record_verification_decision(verified, operator, "approved")

    pending_entry = auth_client.get(
        f"/api/v1/companies/{pending.pk}/panel-entry"
    ).json()
    assert pending_entry["company"]["id"] == pending.pk
    assert pending_entry["view"] == "continue_registration"

    verified_entry = auth_client.get(
        f"/api/v1/companies/{verified.pk}/panel-entry"
    ).json()
    assert verified_entry["company"]["id"] == verified.pk
    assert verified_entry["view"] == "full_panel"
    # No pending-company data leaks into the verified company's payload.
    assert "step_progress" not in verified_entry


def test_credit_is_scoped_per_company(owner):
    from companies.services import record_credit_movement

    first = _register(owner, "one.com", "One")
    second = _register(owner, "two.com", "Two")
    record_credit_movement(first, "charge", 500, "payment")
    # The second company's projection stays zero (SC-010).
    from companies.selectors import credit_projection

    assert credit_projection(first) == 500
    assert credit_projection(second) == 0
