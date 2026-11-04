"""Root API routing, including health and versioned endpoints."""

from django.urls import include, path

from config.api.v1.views import HealthViewSet

urlpatterns = [
    path("health/", HealthViewSet.as_view({"get": "list"}), name="api-health"),
    path("v1/", include("config.api.v1.urls")),
]
