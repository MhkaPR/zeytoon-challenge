"""Notification models (spec 003 data-model.md, FR-041).

This is a general-purpose platform capability: producers raise typed notifications
through :mod:`notifications.interfaces`; recipients are platform users. Delivery is
in-app only (per project decision — no email channel).
"""

from django.conf import settings
from django.db import models

from utils.models import TimestampedModel


class Notification(TimestampedModel):
    """One typed notification event (e.g. a link failure-rate alert)."""

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    event_type = models.CharField(max_length=64, db_index=True)
    severity = models.CharField(
        max_length=16, choices=Severity.choices, default=Severity.WARNING
    )
    subject = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    related_object = models.CharField(max_length=255, blank=True, default="")
    dedup_key = models.CharField(max_length=255, blank=True, default="", db_index=True)
    is_resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications_notification"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.event_type}: {self.subject}"


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


class NotificationDelivery(TimestampedModel):
    """Delivery of one notification to one recipient on one channel (in-app)."""

    class Channel(models.TextChoices):
        IN_APP = "in_app", "In-app"

    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="deliveries"
    )
    recipient = models.ForeignKey(
        NotificationRecipient, on_delete=models.CASCADE, related_name="deliveries"
    )
    channel = models.CharField(
        max_length=16, choices=Channel.choices, default=Channel.IN_APP
    )
    state = models.CharField(
        max_length=16, choices=State.choices, default=State.PENDING
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    error = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "notifications_delivery"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("notification", "recipient", "channel"),
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_delivery_notification_recipient_channel",
            )
        ]

    def __str__(self):
        return f"{self.notification_id}->{self.recipient_id} ({self.channel})"
