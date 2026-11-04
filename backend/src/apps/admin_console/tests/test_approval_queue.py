"""US1 — approval queue and verification decisions (FR-001..FR-006)."""

import pytest
from types import SimpleNamespace

from apps.admin_console.models import Site
from apps.companies import services as company_services
from apps.companies.models import Company

pytestmark = pytest.mark.django_db


def _pending_company(owner):
    return company_services.register_company(
        owner,
        {
            "domain": "queue.example.com",
            "company_name": "Queue Hosting",
            "representative_name": "Rep",
            "phone_number": "02155550000",
        },
    )


def test_queue_lists_pending_companies_with_full_phone(operator_client, owner):
    company = _pending_company(owner)

    response = operator_client.get("/api/v1/ops/approvals")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    entry = body["results"][0]
    assert entry["company_id"] == company.pk
    assert entry["domain"] == "queue.example.com"
    assert entry["phone_number"] == company.phone_number
    assert company.phone_number in str(body)


def test_approval_creates_site_in_onboarding_and_verifies_company(
    operator_client, owner
):
    company = _pending_company(owner)

    response = operator_client.post(
        f"/api/v1/ops/companies/{company.pk}/verification-decisions",
        {"outcome": "approved"},
        format="json",
    )

    assert response.status_code == 201
    company.refresh_from_db()
    assert company.verification_status == Company.VerificationStatus.VERIFIED
    site = Site.objects.get(company=company)
    assert site.domain == company.domain
    assert site.maintenance_state == Site.MaintenanceState.ONBOARDING


def test_approval_enqueues_automatic_site_pipeline_after_commit(
    owner, operator, monkeypatch
):
    company = _pending_company(owner)
    callbacks = []
    enqueued = []
    monkeypatch.setattr(
        "admin_console.services.transaction.on_commit", callbacks.append
    )
    monkeypatch.setattr(
        "admin_console.tasks.run_site_pipeline_task",
        SimpleNamespace(enqueue=lambda site_id: enqueued.append(site_id)),
    )

    from apps.admin_console import services

    services.record_decision(company.pk, operator, "approved")

    assert enqueued == []
    callbacks[0]()
    assert enqueued == [Site.objects.get(company=company).pk]


def test_rejection_suspends_an_existing_site(operator_client, owner):
    company = _pending_company(owner)
    site = Site.objects.create(
        company=company,
        domain=company.domain,
        maintenance_state=Site.MaintenanceState.ONBOARDING,
    )

    response = operator_client.post(
        f"/api/v1/ops/companies/{company.pk}/verification-decisions",
        {"outcome": "not_approved", "note": "invalid documents"},
        format="json",
    )

    assert response.status_code == 201
    company.refresh_from_db()
    assert company.verification_status == Company.VerificationStatus.REJECTED
    site.refresh_from_db()
    assert site.maintenance_state == Site.MaintenanceState.SUSPENDED


def test_reapproval_reactivates_a_suspended_site(operator_client, owner):
    company = _pending_company(owner)
    Site.objects.create(
        company=company,
        domain=company.domain,
        maintenance_state=Site.MaintenanceState.SUSPENDED,
    )

    operator_client.post(
        f"/api/v1/ops/companies/{company.pk}/verification-decisions",
        {"outcome": "approved"},
        format="json",
    )

    site = Site.objects.get(company=company)
    assert site.maintenance_state == Site.MaintenanceState.ONBOARDING
