"""Run pipeline recovery by hand and print what the queue and links look like.

    python manage.py recover_pipeline            # diagnose + recover
    python manage.py recover_pipeline --dry-run  # diagnose only
    python manage.py recover_pipeline --stale-after 900
"""

from collections import Counter

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Diagnose and recover the site pipeline queue."

    def add_arguments(self, parser):
        parser.add_argument("--backend", default="default")
        parser.add_argument("--stale-after", type=int, default=None)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        from django_tasks_db.models import DBTaskResult

        from apps.pipeline.models import CaptureSession, Link
        from apps.pipeline.tasks import recover_site_pipeline_tasks

        self.stdout.write("Task rows by path/status/queue:")
        rows = Counter(
            DBTaskResult.objects.values_list("task_path", "status", "queue_name")
        )
        for key, count in sorted(rows.items(), key=str):
            self.stdout.write(f"  {key}: {count}")
        if not rows:
            self.stdout.write("  (no task rows at all)")

        self.stdout.write("Links by stage/task_state/has_error:")
        links = Counter(
            (stage, state, bool(err))
            for stage, state, err in Link.objects.filter(is_active=True).values_list(
                "pipeline_stage", "pipeline_task_state", "last_error"
            )
        )
        for key, count in sorted(links.items(), key=str):
            self.stdout.write(f"  {key}: {count}")

        self.stdout.write(
            "Open capture sessions: "
            f"{CaptureSession.objects.filter(state__in=CaptureSession.NON_TERMINAL).count()}"
        )
        if opts["dry_run"]:
            return
        result = recover_site_pipeline_tasks(
            backend_name=opts["backend"], stale_after_seconds=opts["stale_after"]
        )
        self.stdout.write(self.style.SUCCESS(f"Recovery: {result}"))