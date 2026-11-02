"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from companies.api import CompanyListCreateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("accounts.urls")),
    path(
        "api/v1/companies",
        CompanyListCreateView.as_view(),
        name="company-list-create-no-slash",
    ),
    path("api/v1/companies/", include("companies.urls")),
    path("api/v1/ops/", include("admin_console.urls")),
    path("api/v1/ops/", include("notifications.urls")),
    path("api/v1/catalog/", include("catalog.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
