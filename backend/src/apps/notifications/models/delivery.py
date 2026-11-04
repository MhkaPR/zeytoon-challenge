"""Per-channel delivery records."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel
from apps.notifications.models.notification import Notification
from apps.notifications.models.recipient import NotificationRecipient


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
