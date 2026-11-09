"""Optional semantic labels."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel


class SemanticLabel(TimestampedModel):
    """An optional LLM semantic label for a table/column (FR-032..FR-034)."""

    table = models.ForeignKey(
        "pipeline.ExtractedTable", on_delete=models.CASCADE, related_name="semantic_labels"
    )
    column = models.ForeignKey(
        "pipeline.ExtractedTableColumn",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="semantic_labels",
    )
    label = models.CharField(max_length=512, blank=True, default="")
    provider = models.CharField(max_length=64, blank=True, default="")
    model = models.CharField(max_length=128, blank=True, default="")
    language = models.CharField(max_length=16, blank=True, default="fa")

    class Meta:
        db_table = "admin_console_semantic_label"
        ordering = ("id",)

    def __str__(self):
        return self.label or f"label {self.pk}"
