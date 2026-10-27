"""Link review tests (US2, FR-009..FR-011, SC-006)."""

import pytest

from admin_console.models import Link, Site

pytestmark = pytest.mark.django_db


def _make_links(site, n=3):
    links = []
    for i in range(n):
        links.append(
            Link.objects.create(
                site=site,
                url=f"https://example.com/{i}",
                url_hash=f"hash{i}",
                source=Link.Source.SITEMAP,
            )
        )
    return links


def test_keep_and_remove_states(operator_client, site):
    links = _make_links(site, 3)
    response = operator_client.post(
        f"/api/v1/ops/sites/{site.pk}/links/review",
        {"keep_ids": [links[0].pk, links[1].pk], "remove_ids": [links[2].pk]},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["kept"] == 2 and body["removed"] == 1
    links[0].refresh_from_db()
    links[2].refresh_from_db()
    assert links[0].review_state == Link.ReviewState.KEPT
    assert links[0].pipeline_stage == Link.PipelineStage.CAPTURE
    assert links[2].review_state == Link.ReviewState.REMOVED
    # Removed link is still recorded.
    assert Link.objects.filter(pk=links[2].pk).exists()
    site.refresh_from_db()
    assert site.maintenance_state == Site.MaintenanceState.ACTIVE


def test_removed_link_not_capture_eligible(operator_client, site):
    links = _make_links(site, 2)
    operator_client.post(
        f"/api/v1/ops/sites/{site.pk}/links/review",
        {"keep_ids": [links[0].pk], "remove_ids": [links[1].pk]},
        format="json",
    )
    kept = Link.objects.filter(
        site=site, review_state=Link.ReviewState.KEPT
    ).count()
    removed = Link.objects.filter(
        site=site, review_state=Link.ReviewState.REMOVED
    ).count()
    assert kept == 1 and removed == 1


def test_review_keeping_none_leaves_site_onboarding(operator_client, site):
    links = _make_links(site, 2)
    response = operator_client.post(
        f"/api/v1/ops/sites/{site.pk}/links/review",
        {"keep_ids": [], "remove_ids": [links[0].pk, links[1].pk]},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "link_not_ready"
    site.refresh_from_db()
    assert site.maintenance_state == Site.MaintenanceState.ONBOARDING
