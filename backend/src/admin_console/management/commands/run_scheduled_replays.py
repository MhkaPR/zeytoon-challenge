"""``run_scheduled_replays``: enqueue one replay task per due link (FR-037, R2).

Dispatching goes through ``django.tasks`` (never Celery); the immediate backend runs the
tasks inline, a queued backend hands them to a worker.
"""

from django.core.management.base import BaseCommand

from admin_console import services


class Command(BaseCommand):
    help = "Replay every link that is due for a scheduled replay cycle."

    def handle(self, *args, **options):
        from admin_console.tasks import run_replay_task

        links = services.due_links()
        enqueued = 0
        for link in links:
            run_replay_task.enqueue(link.pk)
            enqueued += 1
        self.stdout.write(
            f"run_scheduled_replays: enqueued {enqueued} replay task(s) "
            f"for {len(links)} due link(s)."
        )
