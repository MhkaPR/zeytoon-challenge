"""Owner-scoping tests (US2, FR-028, SC-006)."""

import pytest

from companies.services import register_company

pytestmark = pytest.mark.django_db


def _register(owner, domain):
    return register_company(
        owner,
        {
            "domain": domain,
            "company_name": "Co",
            "representative_name": "Rep",
            "phone_number": "02123456789",
        },
    )


def test_other_owners_company_is_not_found_on_every_endpoint(auth_client, other_owner):
    company = _register(other_owner, "theirs.com")
    pk = company.pk
    for url in [
        f"/api/v1/companies/{pk}",
        f"/api/v1/companies/{pk}/panel-entry",
        f"/api/v1/companies/{pk}/panel",
        f"/api/v1/companies/{pk}/plan-eligibility",
        f"/api/v1/companies/{pk}/credit",
    ]:
        response = auth_client.get(url)
        assert response.status_code == 404, url
        assert response.json()["error"]["code"] == "not_found"


def test_anonymous_requests_are_refused(api_client, owner):
    company = _register(owner, "mine.com")
    response = api_client.get(f"/api/v1/companies/{company.pk}/panel-entry")
    assert response.status_code == 401
