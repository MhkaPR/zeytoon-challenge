"""Credit-ledger tests (US4, FR-033, FR-034, SC-010, SC-013)."""

import pytest

from companies.models import CreditLedgerEntry
from companies.selectors import credit_projection
from companies.services import record_credit_movement, register_company

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


def test_projection_starts_at_zero(owner):
    company = _register(owner)
    assert credit_projection(company) == 0


def test_charge_then_decharge_projection(owner):
    company = _register(owner)
    record_credit_movement(company, "charge", 1000, "payment")
    record_credit_movement(company, "decharge", 250, "platform_view")
    assert credit_projection(company) == 750
    assert CreditLedgerEntry.objects.filter(company=company).count() == 2


def test_amount_must_be_positive(owner):
    from accounts.exceptions import ApiError

    company = _register(owner)
    with pytest.raises(ApiError) as exc:
        record_credit_movement(company, "charge", 0, "payment")
    assert exc.value.code == "invalid_movement"


def test_unknown_reason_is_rejected(owner):
    from accounts.exceptions import ApiError

    company = _register(owner)
    with pytest.raises(ApiError):
        record_credit_movement(company, "charge", 10, "nonsense")


def test_entries_are_immutable(owner):
    company = _register(owner)
    entry = record_credit_movement(company, "charge", 100, "payment")
    entry.amount = 999
    with pytest.raises(ValueError):
        entry.save()
    with pytest.raises(ValueError):
        entry.delete()


def test_credit_is_per_company(owner):
    first = _register(owner, "one.com")
    second = _register(owner, "two.com")
    record_credit_movement(first, "charge", 500, "payment")
    assert credit_projection(first) == 500
    assert credit_projection(second) == 0


def test_projection_equals_running_total(owner):
    company = _register(owner)
    for amount in (100, 50, 25):
        record_credit_movement(company, "charge", amount, "payment")
    record_credit_movement(company, "decharge", 30, "platform_view")
    entries = list(company.credit_entries.all())
    total = sum(
        e.amount if e.direction == "charge" else -e.amount for e in entries
    )
    assert credit_projection(company) == total == 145


def test_credit_endpoint(auth_client, owner):
    company = _register(owner)
    record_credit_movement(company, "charge", 300, "payment")
    response = auth_client.get(f"/api/v1/companies/{company.pk}/credit")
    assert response.status_code == 200
    body = response.json()
    assert body["current_credit"] == 300
    assert len(body["entries"]) == 1
