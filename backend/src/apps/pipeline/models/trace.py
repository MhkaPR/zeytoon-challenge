"""Stored capture trace metadata."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel


class Trace(TimestampedModel):
    """Metadata for a domtrack trace stored as an artifact (FR-000a, FR-019).

    The trace body is never stored in a database column; only the storage key, backend
    alias, byte size, and hash are kept. Capture is server-side, so no operator is
    recorded.
    """

    class Origin(models.TextChoices):
        SERVER_CAPTURE = "server_capture", "Server capture"
        REPLAY_RECORDING = "replay_recording", "Replay recording"

    link = models.ForeignKey("pipeline.Link", on_delete=models.CASCADE, related_name="traces")
    capture_session = models.ForeignKey(
        "pipeline.CaptureSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="traces",
    )
    captured_at = models.DateTimeField()
    origin = models.CharField(
        max_length=32,
        choices=Origin.choices,
        default=Origin.SERVER_CAPTURE,
    )
    storage_key = models.CharField(max_length=512)
    storage_backend = models.CharField(max_length=64, default="default")
    content_sha256 = models.CharField(max_length=64, db_index=True)
    is_valid_trace = models.BooleanField(default=False)

    class Meta:
        db_table = "admin_console_trace"
        ordering = ("-captured_at",)

    def __str__(self):
        return self.storage_key
