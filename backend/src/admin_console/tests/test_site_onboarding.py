"""US2 — site onboarding + discovery endpoints (FR-007, FR-011)."""

import pytest

from admin_console import services
from admin_console.models import Link, Site

pytestmark = pytest.mark.django_db


def test_onboard_site_returns_201_with_onboarding_state(operator_client, approved_company):
    response = operator_client.post(
        "/api/v1/ops/sites", {"company_id": approved_company.pk}, format="json"
    )

    assert response.status_code == 201
    site = Site.objects.get(company=approved_company)
    assert response.json()["site"]["id"] == site.pk
    assert site.maintenance_state == Site.MaintenanceState.ONBOARDING


def test_second_site_for_the_same_company_is_refused(operator_client, site):
    response = operator_client.post(
        "/api/v1/ops/sites", {"company_id": site.company_id}, format="json"
    )
    assert response.status_code == 409


def test_discovery_stores_candidate_links(operator_client, site, stub_discovery):
    stub_discovery.urls = ["https://example.com/plans", "https://example.com/plans"]

    response = operator_client.post(
        f"/api/v1/ops/sites/{site.pk}/discover-links", {}, format="json"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["after_policy"] == 1
    assert body["candidates"][0]["source"] == Link.Source.ADAPTIVE_CRAWL
    assert Link.objects.filter(site=site).count() == 1
    assert stub_discovery.calls  # the query set was passed to the crawler


def test_manual_links_are_stored(operator_client, site):
    response = operator_client.post(
        f"/api/v1/ops/sites/{site.pk}/links",
        {"urls": ["https://example.com/manual"]},
        format="json",
    )
    assert response.status_code == 201
    link = Link.objects.get(site=site)
    assert link.source == Link.Source.MANUAL


def test_empty_crawl_keeps_site_in_onboarding_and_notifies(
    site, stub_discovery, notification_recipient
):
    site.maintenance_state = Site.MaintenanceState.ONBOARDING
    site.save(update_fields=["maintenance_state", "updated_at"])
    stub_discovery.urls = []

    result = services.discover_and_store_links(site)

    assert result["links"] == []
    site.refresh_from_db()
    assert site.maintenance_state == Site.MaintenanceState.ONBOARDING
    from notifications.models import Notification

    assert Notification.objects.filter(event_type="link_discovery_empty").exists()
