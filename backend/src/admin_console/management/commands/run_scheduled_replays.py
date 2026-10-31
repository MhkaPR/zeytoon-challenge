"""Enqueue one replay task per due link (no Celery; ``django.tasks``).

Due = an active site with a kept link whose ``last_replay_at`` is older than the
configured replay period. Suspended sites are skipped (FR-039).
"""

from django.core.management.base import BaseCommand

from admin_console import services, tasks


class Command(BaseCommand):
    help = "Enqueue scheduled replay tasks for links that are due."

    def handle(self, *args, **options):
        links = services.due_links()
        for link in links:
            tasks.run_replay_task.enqueue(link.pk)
        self.stdout.write(f"Enqueued {len(links)} replay task(s).")
