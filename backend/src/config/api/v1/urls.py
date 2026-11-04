"""Version 1 API route aggregation."""

from django.urls import include, path
from companies.api import CompanyListCreateView

urlpatterns = [
    path("auth/", include("accounts.urls")),
    path(
        "companies",
        CompanyListCreateView.as_view(),
        name="company-list-create-no-slash",
    ),
    path("companies/", include("companies.urls")),
    path("ops/", include("admin_console.urls")),
    path("ops/", include("notifications.urls")),
    path("catalog/", include("catalog.urls")),
]
