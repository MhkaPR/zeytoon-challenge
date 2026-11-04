"""US2 — site onboarding + discovery endpoints (FR-007, FR-011)."""

import pytest

from apps.admin_console import services
from apps.pipeline.models import Link, Site

pytestmark = pytest.mark.django_db


def test_onboard_site_returns_201_with_onboarding_state(
    operator_client, approved_company
):
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


def test_site_list_includes_pipeline_stage_counts(operator_client, site):
    Link.objects.create(
        site=site,
        url="https://example.com/plans",
        url_hash="plans-hash",
        pipeline_stage=Link.PipelineStage.CAPTURED,
    )

    response = operator_client.get("/api/v1/ops/sites")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["links_count"] == 1
    assert payload["results"][0]["stage_counts"][Link.PipelineStage.CAPTURED] == 1


def test_site_detail_includes_links(operator_client, site):
    link = Link.objects.create(
        site=site,
        url="https://example.com/plans",
        url_hash="detail-plans-hash",
    )

    response = operator_client.get(f"/api/v1/ops/sites/{site.pk}")

    assert response.status_code == 200
    assert response.json()["site"]["id"] == site.pk
    assert response.json()["links"][0]["id"] == link.pk


def test_site_links_endpoint_returns_client_expected_shape(operator_client, site):
    link = Link.objects.create(
        site=site,
        url="https://example.com/links",
        url_hash="links-endpoint-hash",
    )

    response = operator_client.get(f"/api/v1/ops/sites/{site.pk}/links")

    assert response.status_code == 200
    assert response.json()["links"][0]["id"] == link.pk


def test_site_detail_and_links_list_use_only_pipeline_summary_columns(
    operator_client, site
):
    link = Link.objects.create(
        site=site,
        url="https://example.com/progress",
        url_hash="progress-summary-hash",
        pipeline_stage=Link.PipelineStage.CAPTURED,
    )

    detail = operator_client.get(f"/api/v1/ops/sites/{site.pk}")
    link_list = operator_client.get(f"/api/v1/ops/sites/{site.pk}/links")

    assert detail.status_code == 200
    assert detail.json()["links"][0]["id"] == link.pk
    assert link_list.status_code == 200
    assert link_list.json()["links"][0]["pipeline_stage"] == Link.PipelineStage.CAPTURED


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
    from apps.notifications.models import Notification

    assert Notification.objects.filter(event_type="link_discovery_empty").exists()
