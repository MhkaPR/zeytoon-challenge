"""Version 1 API route aggregation."""

from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.accounts.urls")),
    path("companies/", include("apps.companies.urls")),
    path("ops/", include("apps.admin_console.urls")),
    path("ops/", include("apps.notifications.urls")),
    path("catalog/", include("apps.catalog.urls")),
]
