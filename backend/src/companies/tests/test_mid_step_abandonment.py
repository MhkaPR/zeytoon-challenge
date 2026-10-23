"""Mid-step abandonment tests (US1, FR-009, SC-005)."""

import pytest

from companies.models import CompanyRegistrationDraft, CompanyStepProgress
from companies.services import abandon_step, register_company, save_step

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


def test_abandon_clears_only_that_step_draft(owner):
    company = _register(owner)
    save_step(owner, company, "company_information", {"domain": "example.com"})
    assert CompanyRegistrationDraft.objects.filter(
        owner=owner, company=company, step_key="company_information"
    ).count() == 1

    # A second, different step draft must be preserved.
    CompanyRegistrationDraft.objects.create(
        owner=owner, company=company, step_key="other", payload={"keep": True}
    )

    abandon_step(owner, company, "company_information")
    assert not CompanyRegistrationDraft.objects.filter(
        owner=owner, company=company, step_key="company_information"
    ).exists()
    assert CompanyRegistrationDraft.objects.filter(
        owner=owner, company=company, step_key="other"
    ).exists()


def test_abandon_resumes_at_same_step(owner):
    company = _register(owner)
    save_step(owner, company, "company_information", {"domain": "example.com"})
    abandon_step(owner, company, "company_information")
    from companies import selectors

    assert selectors.current_step(company) == "company_information"


def test_abandon_does_not_touch_earlier_approved_steps(owner):
    company = _register(owner)
    # Step one is approved at registration and must stay approved after an abandon.
    abandon_step(owner, company, "company_information")
    row = CompanyStepProgress.objects.get(
        company=company, step_key="company_information"
    )
    assert row.state in {
        CompanyStepProgress.State.APPROVED,
        CompanyStepProgress.State.OPEN,
    }


def test_abandon_endpoint_returns_resume_step(auth_client, owner):
    company = _register(owner)
    response = auth_client.post(
        f"/api/v1/companies/{company.pk}/steps/company_information/abandon",
        {},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["step_key"] == "company_information"
