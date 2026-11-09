from django.apps import AppConfig


class UtilsConfig(AppConfig):
    name = "apps.utils"

    def ready(self):
        """Register project models for actor-aware audit history."""
        from django.apps import apps
        from auditlog.registry import auditlog

        project_apps = {
            "accounts",
            "companies",
            "admin_console",
            "catalog",
            "pipeline",
            "recommendations",
        }
        for model in apps.get_models():
            if model._meta.app_label in project_apps and not model._meta.proxy:
                auditlog.register(model)
