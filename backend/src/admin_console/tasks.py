"""Django Tasks (``django.tasks``) task bodies — no Celery anywhere (research R2).

Module-level functions wrapped with ``@task`` so the immediate backend runs them
synchronously in tests and a queued backend can run them in a worker in production.
Each body is per-link isolated (FR-051).
"""

from django.tasks import task


@task
def run_capture_task(link_id, duration_ms=None):
    """Run a headless capture for a link (FR-016..FR-019)."""
    from admin_console.models import Link
    from admin_console.services import start_capture

    return start_capture(Link.objects.get(pk=link_id), duration_ms=duration_ms)


@task
def run_extraction_task(link_id):
    """Extract tables for a link (FR-020..FR-022)."""
    from admin_console.models import Link
    from admin_console.services import extract_link_tables

    return extract_link_tables(Link.objects.get(pk=link_id))


@task
def run_classification_task(link_id):
    """Classify tables for a link (FR-023..FR-025)."""
    from admin_console.models import Link
    from admin_console.services import classify_link_tables

    return classify_link_tables(Link.objects.get(pk=link_id))


@task
def run_plan_extraction_task(link_id):
    """Extract plan data for a link (FR-026..FR-031)."""
    from admin_console.models import Link
    from admin_console.services import extract_link_plans

    return extract_link_plans(Link.objects.get(pk=link_id))


@task
def run_labeling_task(link_id):
    """Label tables for a link (FR-032..FR-035)."""
    from admin_console.models import Link
    from admin_console.services import label_link_tables

    return label_link_tables(Link.objects.get(pk=link_id))


@task
def run_replay_task(link_id):
    """Run one replay cycle for a link (FR-039..FR-043)."""
    from admin_console.models import Link
    from admin_console.replay import execute_replay_run

    return execute_replay_run(Link.objects.get(pk=link_id))
