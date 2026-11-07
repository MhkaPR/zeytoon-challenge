"""Enqueue the periodic recommendation-space refresh."""

from django.core.management.base import BaseCommand

from apps.recommendations.tasks import refresh_plan_space_task


class Command(BaseCommand):
    help = "Enqueue a recommendation-space refresh."

    def handle(self, *args, **options):
        result = refresh_plan_space_task.enqueue()
        self.stdout.write(f"Enqueued recommendation space refresh: {result}")
