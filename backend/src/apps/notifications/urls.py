"""Notifications routes, mounted under /api/v1/ops/ (FR-041)."""

from rest_framework.routers import SimpleRouter

from apps.notifications.views.v1 import api

app_name = "notifications"

router = SimpleRouter(trailing_slash=False)
router.register("", api.NotificationInboxViewSet, basename="notification-inbox")
router.register(
    "notification-recipients",
    api.NotificationRecipientViewSet,
    basename="notification-recipient",
)

urlpatterns = router.urls
