"""Django Tasks (``django.tasks``) task bodies — no Celery anywhere (research R2).

Module-level functions wrapped with ``@task`` so the immediate backend runs them
synchronously in tests and a queued backend can run them in a worker in production.
"""

from django.tasks import task


@task
def run_extraction_task(link_id):
    """Extract tables for a link (FR-018, FR-019)."""
    from admin_console.models import Link
    from admin_console.services import extract_tables_for_link

    link = Link.objects.get(pk=link_id)
    return extract_tables_for_link(link)


@task
def run_labeling_task(link_id, actor_id=None):
    """Label tables for a link (FR-021)."""
    from admin_console.models import Link
    from admin_console.services import label_tables_for_link

    link = Link.objects.get(pk=link_id)
    return label_tables_for_link(link, actor_id=actor_id)


@task
def run_replay_task(link_id):
    """Run one replay cycle for a link (FR-037, FR-038)."""
    from admin_console.models import Link
    from admin_console.replay import execute_replay_run

    link = Link.objects.get(pk=link_id)
    return execute_replay_run(link)
