"""Site onboarding contract tests (US2, FR-007, FR-008, SC-005)."""

import pytest

from admin_console.models import Link, Site

pytestmark = pytest.mark.django_db


def test_onboard_site_creates_single_site(operator_client, approved_company):
    response = operator_client.post(
        "/api/v1/ops/sites", {"company_id": approved_company.pk}, format="json"
    )
    assert response.status_code == 201
    body = response.json()
    assert body["site"]["maintenance_state"] == "onboarding"
    assert Site.objects.filter(company=approved_company).count() == 1


def test_second_site_is_refused(operator_client, approved_company):
    operator_client.post(
        "/api/v1/ops/sites", {"company_id": approved_company.pk}, format="json"
    )
    response = operator_client.post(
        "/api/v1/ops/sites", {"company_id": approved_company.pk}, format="json"
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_field"


def test_onboarding_unapproved_company_is_refused(operator_client, company):
    response = operator_client.post(
        "/api/v1/ops/sites", {"company_id": company.pk}, format="json"
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "link_not_ready"


def test_sitemap_discovery_stores_candidates(operator_client, site, monkeypatch):
    from admin_console import discovery

    monkeypatch.setattr(
        discovery,
        "discover_site_links",
        lambda domain, fetcher=None: (
            "https://example.com/sitemap.xml",
            ["https://example.com/a", "https://example.com/b"],
        ),
    )
    response = operator_client.post(f"/api/v1/ops/sites/{site.pk}/discover-links")
    assert response.status_code == 200
    body = response.json()
    assert body["has_sitemap"] is True
    assert body["discovered"] == 2
    assert Link.objects.filter(site=site, source="sitemap").count() == 2


def test_no_sitemap_reports_zero(operator_client, site, monkeypatch):
    from admin_console import discovery

    monkeypatch.setattr(
        discovery, "discover_site_links", lambda domain, fetcher=None: ("", [])
    )
    response = operator_client.post(f"/api/v1/ops/sites/{site.pk}/discover-links")
    body = response.json()
    assert body["has_sitemap"] is False
    assert body["discovered"] == 0


def test_manual_links_are_stored(operator_client, site):
    response = operator_client.post(
        f"/api/v1/ops/sites/{site.pk}/links",
        {"urls": ["https://example.com/x", "https://example.com/y"]},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["discovered"] == 2
    assert Link.objects.filter(site=site, source="manual").count() == 2


def test_discovery_is_idempotent(operator_client, site, monkeypatch):
    from admin_console import discovery

    monkeypatch.setattr(
        discovery,
        "discover_site_links",
        lambda domain, fetcher=None: (
            "https://example.com/sitemap.xml",
            ["https://example.com/a"],
        ),
    )
    operator_client.post(f"/api/v1/ops/sites/{site.pk}/discover-links")
    second = operator_client.post(f"/api/v1/ops/sites/{site.pk}/discover-links")
    assert second.json()["discovered"] == 0
    assert Link.objects.filter(site=site).count() == 1
