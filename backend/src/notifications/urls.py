"""Notifications routes, mounted under /api/v1/ops/ (FR-041)."""

from django.urls import path

from notifications import api

app_name = "notifications"

urlpatterns = [
    path("notifications", api.NotificationInboxView.as_view(), name="inbox"),
    path(
        "notification-recipients",
        api.NotificationRecipientListCreateView.as_view(),
        name="recipient-list-create",
    ),
    path(
        "notification-recipients/<int:recipient_id>/deactivate",
        api.NotificationRecipientDeactivateView.as_view(),
        name="recipient-deactivate",
    ),
]
