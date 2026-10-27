"""Replay scheduler tests (US8, FR-037, FR-043, research R2)."""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from admin_console.models import Link, Site
from admin_console.services import due_links

pytestmark = pytest.mark.django_db


def test_due_links_selects_only_overdue_active_links(published_link):
    link = published_link
    # Never replayed -> due.
    assert link in due_links()

    link.last_replay_at = timezone.now()
    link.save(update_fields=["last_replay_at", "updated_at"])
    assert link not in due_links()

    link.last_replay_at = timezone.now() - timedelta(days=2)
    link.save(update_fields=["last_replay_at", "updated_at"])
    assert link in due_links()


def test_suspended_site_links_are_skipped(published_link):
    published_link.site.maintenance_state = Site.MaintenanceState.SUSPENDED
    published_link.site.save(update_fields=["maintenance_state", "updated_at"])
    assert published_link not in due_links()


def test_link_without_complete_recipe_is_skipped(published_link):
    published_link.recipes.filter(is_current=True).update(is_complete=False)
    assert published_link not in due_links()


def test_management_command_enqueues_one_task_per_due_link(published_link, monkeypatch):
    from admin_console import tasks

    calls = []

    class _FakeTask:
        def enqueue(self, link_id):
            calls.append(link_id)

    monkeypatch.setattr(tasks, "run_replay_task", _FakeTask())
    call_command("run_scheduled_replays")
    assert published_link.pk in calls


def test_management_command_uses_django_tasks_not_celery(published_link):
    from django.tasks import default_task_backend

    assert default_task_backend is not None
    import admin_console.tasks as tasks

    assert hasattr(tasks.run_replay_task, "enqueue")
