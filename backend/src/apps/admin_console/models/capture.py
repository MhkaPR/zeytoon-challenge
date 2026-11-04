"""Headless capture attempt."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel
from apps.admin_console.models.link import Link
from apps.admin_console.models.trace import Trace


class CaptureSession(TimestampedModel):
    """One server-side headless capture attempt (FR-016..FR-018)."""

    class Mode(models.TextChoices):
        HEADLESS_FIXED = "headless_fixed", "Headless fixed"

    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        RECORDING = "recording", "Recording"
        STORED = "stored", "Stored"
        FAILED = "failed", "Failed"

    NON_TERMINAL = (State.PENDING, State.RECORDING)

    link = models.ForeignKey(
        Link, on_delete=models.CASCADE, related_name="capture_sessions"
    )
    mode = models.CharField(
        max_length=16, choices=Mode.choices, default=Mode.HEADLESS_FIXED
    )
    state = models.CharField(
        max_length=16, choices=State.choices, default=State.PENDING
    )
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    error = models.CharField(max_length=512, blank=True, default="")
    trace = models.ForeignKey(
        "admin_console.Trace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="capture_sessions",
    )

    class Meta:
        db_table = "admin_console_capture_session"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("link",),
                condition=models.Q(
                    state__in=("pending", "recording"), deleted_at__isnull=True
                ),
                name="uniq_nonterminal_capture_session_per_link",
            ),
        ]

    def __str__(self):
        return f"capture {self.pk} ({self.state})"
