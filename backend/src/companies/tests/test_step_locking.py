"""Step-locking tests (US1, FR-008, FR-011)."""

import pytest
from accounts.exceptions import ApiError

from companies import steps
from companies.models import CompanyStepProgress
from companies.services import register_company

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


def test_locked_verification_step_is_refused(owner):
    company = _register(owner)
    with pytest.raises(ApiError) as exc:
        steps.assert_step_enterable(company, "verification")
    assert exc.value.code == "step_locked"
    assert exc.value.status_code == 403


def test_step_one_is_enterable(owner):
    company = _register(owner)
    row = steps.assert_step_enterable(company, "company_information")
    assert row.step_key == "company_information"


def test_unknown_step_is_not_found(owner):
    company = _register(owner)
    with pytest.raises(ApiError) as exc:
        steps.assert_step_enterable(company, "nope")
    assert exc.value.status_code == 404


def test_verification_step_needs_no_owner_input(owner):
    from companies import constants

    definitions = {step["key"]: step for step in constants.step_definitions()}
    assert definitions["company_information"]["owner_input"] is True
    assert definitions["verification"]["owner_input"] is False


def test_approval_unlocks_verification_step(owner, operator):
    from companies.services import record_verification_decision

    company = _register(owner)
    record_verification_decision(company, operator, "approved")
    company.refresh_from_db()
    row = steps.assert_step_enterable(company, "verification")
    assert row.state == CompanyStepProgress.State.APPROVED
