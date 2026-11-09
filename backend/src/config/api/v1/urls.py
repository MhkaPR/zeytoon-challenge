"""Version 1 API route aggregation."""

from django.urls import include, path

urlpatterns = [
    path("auth", include("apps.accounts.urls")),
    path("auth/", include("apps.accounts.urls")),
    path("companies", include("apps.companies.urls")),
    path("companies/", include("apps.companies.urls")),
    path("ops", include("apps.admin_console.urls")),
    path("ops/", include("apps.admin_console.urls")),
    path("catalog", include("apps.catalog.urls")),
    path("catalog/", include("apps.catalog.urls")),
    path("recommendations", include("apps.recommendations.urls")),
    path("recommendations/", include("apps.recommendations.urls")),
]
