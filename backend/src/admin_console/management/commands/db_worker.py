from django_tasks_db.management.commands.db_worker import (
    Command as DatabaseWorkerCommand,
)

from admin_console.tasks import recover_site_pipeline_tasks


class Command(DatabaseWorkerCommand):
    help = "Run a database worker and recover interrupted site pipelines on startup."

    def handle(self, *args, **options):
        recovery = recover_site_pipeline_tasks(
            backend_name=options.get("backend_name", "default")
        )
        self.stdout.write(
            "Recovered "
            f"{recovery['recovered']} interrupted pipeline task(s); "
            f"enqueued {recovery['enqueued_sites']} unfinished site(s)."
        )
        return super().handle(*args, **options)
