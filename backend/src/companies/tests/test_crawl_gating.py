"""Crawl-gating tests (US4, FR-034a, FR-035)."""

import pytest

from companies.models import Company, CreditLedgerEntry
from companies.services import register_company, set_crawl_enabled

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


def test_enabling_crawl_requires_charged(owner):
    from accounts.exceptions import ApiError

    company = _register(owner)
    with pytest.raises(ApiError) as exc:
        set_crawl_enabled(company, True)
    assert exc.value.code == "company_requirement_missing"
    assert exc.value.fields["missing"] == ["charged"]


def test_enabling_crawl_costs_nothing(owner):
    company = _register(owner)
    company.charge_status = Company.ChargeStatus.CHARGED
    company.save(update_fields=["charge_status"])
    set_crawl_enabled(company, True)
    company.refresh_from_db()
    assert company.crawl_enabled is True
    assert CreditLedgerEntry.objects.filter(company=company).count() == 0


def test_crawl_endpoint_blocked_when_uncharged(auth_client, owner):
    company = _register(owner)
    response = auth_client.post(
        f"/api/v1/companies/{company.pk}/crawl", {"enabled": True}, format="json"
    )
    assert response.status_code == 409
    assert response.json()["error"]["fields"]["missing"] == ["charged"]


def test_crawl_endpoint_enabled_when_charged(auth_client, owner):
    company = _register(owner)
    company.charge_status = Company.ChargeStatus.CHARGED
    company.save(update_fields=["charge_status"])
    response = auth_client.post(
        f"/api/v1/companies/{company.pk}/crawl", {"enabled": True}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["credit_unchanged"] is True
