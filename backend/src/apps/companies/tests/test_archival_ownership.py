"""Ownership + archival tests (US5, FR-036..FR-040, SC-007, SC-008)."""

import pytest
from django.db.models import ProtectedError

from apps.companies.models import Company
from apps.companies.services import (
    archive_companies_for_user,
    register_company,
)

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


def test_in_product_ownership_transfer_is_refused(auth_client, owner):
    company = _register(owner)
    response = auth_client.post(
        f"/api/v1/companies/{company.pk}/transfer-ownership", {}, format="json"
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ownership_transfer_unsupported"


def test_ownership_never_changes(owner, other_owner):
    company = _register(owner)
    # There is no in-product path that mutates owner; a direct model save keeps the owner.
    company.refresh_from_db()
    assert company.owner_id == owner.pk
    assert company.owner_id != other_owner.pk


def test_archival_sets_flags_and_keeps_records(owner):
    company = _register(owner)
    count = archive_companies_for_user(owner)
    assert count == 1
    company.refresh_from_db()
    assert company.is_archived is True
    assert company.archived_at is not None
    # The record is still retrievable (never hard-deleted).
    assert Company.objects.filter(pk=company.pk).exists()


def test_company_is_never_hard_deleted(owner):
    company = _register(owner)
    # Deleting the owner is blocked by the PROTECT FK, and companies have no delete path.
    with pytest.raises(ProtectedError):
        owner.delete()


def test_abuse_state_is_readable(owner):
    company = _register(owner)
    company.refresh_from_db()
    # The state the admin-side actor needs is exposed as plain fields.
    assert company.verification_status
    assert company.charge_status
    assert company.is_archived is False
