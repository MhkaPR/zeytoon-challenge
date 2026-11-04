"""Notification recipients."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel


class NotificationRecipient(TimestampedModel):
    """A platform user who receives notifications (admin-managed, FR-041)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_recipients",
    )
    name = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_recipients_created",
    )

    class Meta:
        db_table = "notifications_recipient"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user",),
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_notification_recipient_user",
            )
        ]

    def __str__(self):
        return self.name or str(self.user_id)
