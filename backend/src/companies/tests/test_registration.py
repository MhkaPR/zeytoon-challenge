"""Contract tests for company registration (contracts/companies-api.md, US1)."""

import pytest

from companies.models import Company, CompanyStepProgress
from companies.services import register_company

pytestmark = pytest.mark.django_db

LIST_URL = "/api/v1/companies/"


def _payload(**overrides):
    data = {
        "domain": "example.com",
        "company_name": "Example Hosting",
        "representative_name": "Ali Rezaei",
        "phone_number": "02123456789",
    }
    data.update(overrides)
    return data


def test_create_company_pending_unverified(auth_client, owner):
    response = auth_client.post(LIST_URL, _payload(), format="json")
    assert response.status_code == 201
    body = response.json()
    assert body["company"]["verification_status"] == "pending"
    assert body["company"]["unverified"] is True
    company = Company.objects.get(pk=body["company"]["id"])
    assert company.owner_id == owner.pk


def test_create_company_without_trailing_slash(auth_client):
    response = auth_client.post(LIST_URL.rstrip("/"), _payload(), format="json")

    assert response.status_code == 201
    assert response.json()["company"]["verification_status"] == "pending"


def test_internal_number_is_optional(auth_client):
    response = auth_client.post(
        LIST_URL, _payload(internal_number=""), format="json"
    )
    assert response.status_code == 201


def test_mandatory_field_missing_names_field_and_creates_nothing(auth_client):
    payload = _payload()
    del payload["company_name"]
    response = auth_client.post(LIST_URL, payload, format="json")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_field"
    assert "company_name" in str(response.json()["error"]["fields"])
    assert Company.objects.count() == 0


def test_list_is_owner_scoped(auth_client, owner, other_owner):
    register_company(
        other_owner,
        _payload(domain="other.com", company_name="Other"),
    )
    response = auth_client.get(LIST_URL)
    assert response.status_code == 200
    assert response.json()["companies"] == []


def test_domain_is_stored_normalized_and_not_deduplicated(owner):
    first = register_company(owner, _payload(domain="WWW.Example.com/path?x=1"))
    assert first.domain == "example.com"
    # A repeated domain is accepted; this feature performs no detection (FR-041/FR-042).
    second = register_company(owner, _payload(company_name="Again"))
    assert second.pk != first.pk
    assert Company.objects.filter(owner=owner).count() == 2


def test_registration_seeds_step_progress(owner):
    company = register_company(owner, _payload())
    states = {
        row.step_key: row.state
        for row in CompanyStepProgress.objects.filter(company=company)
    }
    assert states["company_information"] == CompanyStepProgress.State.APPROVED
    assert states["verification"] == CompanyStepProgress.State.LOCKED
