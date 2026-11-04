"""US10 — scheduled replay selection and enqueue (no Celery)."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.admin_console import services, tasks
from apps.admin_console.models import Link, Site

pytestmark = pytest.mark.django_db


def _kept_link(site, url_hash, last_replay_at=None):
    return Link.objects.create(
        site=site,
        url=f"https://example.com/{url_hash}",
        url_hash=url_hash,
        review_state=Link.ReviewState.KEPT,
        pipeline_stage=Link.PipelineStage.PUBLISHED,
        is_active=True,
        last_replay_at=last_replay_at,
    )


def test_due_links_excludes_suspended_sites_and_non_kept_links(site):
    stale = timezone.now() - timedelta(days=2)
    due = _kept_link(site, "due", last_replay_at=stale)
    _kept_link(site, "fresh", last_replay_at=timezone.now())
    Link.objects.create(
        site=site,
        url="https://example.com/dropped",
        url_hash="dropped",
        review_state=Link.ReviewState.DROPPED,
        last_replay_at=stale,
    )

    assert services.due_links() == [due]


def test_due_links_skips_suspended_sites(owner, site):
    from apps.companies import services as company_services

    other = company_services.register_company(
        owner,
        {
            "domain": "suspended.example.com",
            "company_name": "Suspended Host",
            "representative_name": "Rep",
            "phone_number": "02100000000",
        },
    )
    suspended = Site.objects.create(
        company=other,
        domain=other.domain,
        maintenance_state=Site.MaintenanceState.SUSPENDED,
    )
    _kept_link(
        suspended, "suspended-link", last_replay_at=timezone.now() - timedelta(days=2)
    )
    # The active site has one due link; the suspended site's link must be excluded.
    due = _kept_link(
        site, "active-link", last_replay_at=timezone.now() - timedelta(days=2)
    )

    assert services.due_links() == [due]


def test_scheduler_command_enqueues_one_task_per_due_link(site, monkeypatch):
    stale = timezone.now() - timedelta(days=2)
    link = _kept_link(site, "due", last_replay_at=stale)
    enqueued = []
    monkeypatch.setattr(
        tasks,
        "run_replay_task",
        SimpleNamespace(enqueue=lambda pk: enqueued.append(pk)),
    )

    call_command("run_scheduled_replays")

    assert enqueued == [link.pk]
