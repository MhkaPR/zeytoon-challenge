from django.apps import AppConfig


class CompaniesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "companies"

    def ready(self):
        # Connect the accounts account-deletion signal to company archival (FR-038).
        from apps.companies import signals  # noqa: F401
