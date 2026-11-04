"""Typed notification events."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel


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
