"""Operator console routes, mounted under /api/v1/ops/."""

from rest_framework.routers import DefaultRouter

from apps.admin_console.views.v1.admin_console import OpsViewSet

app_name = "admin_console"

router = DefaultRouter(trailing_slash=False)
router.register("", OpsViewSet, basename="ops")

urlpatterns = router.urls
