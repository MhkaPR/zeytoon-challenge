"""Failure alerts."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel
from apps.admin_console.models.link import Link


class FailureAlert(TimestampedModel):
    """A link-state alert raised when a link's failure rate crosses threshold (FR-044)."""

    class State(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    link = models.ForeignKey(
        Link, on_delete=models.CASCADE, related_name="failure_alerts"
    )
    state = models.CharField(max_length=16, choices=State.choices, default=State.OPEN)
    failure_rate = models.FloatField(default=0.0)
    raised_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    notification_dedup_key = models.CharField(
        max_length=255, blank=True, default="", db_index=True
    )

    class Meta:
        db_table = "admin_console_failure_alert"
        ordering = ("-created_at",)

    def __str__(self):
        return f"alert {self.pk} ({self.state})"
