"""Extracted plan records."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel
from apps.admin_console.models.table import ExtractedTable
from apps.admin_console.models.link import Link
from apps.admin_console.models.classification import TableClassification


class PlanRecord(TimestampedModel):
    """A normalized plan extracted from a plans table (FR-026..FR-031).

    ``values`` is keyed by schema field key; it contains data only — no selectors and
    no formulas.
    """

    link = models.ForeignKey(
        Link, on_delete=models.CASCADE, related_name="plan_records"
    )
    table = models.ForeignKey(
        ExtractedTable, on_delete=models.CASCADE, related_name="plan_records"
    )
    classification = models.ForeignKey(
        TableClassification,
        on_delete=models.CASCADE,
        related_name="plan_records",
    )
    plan_type = models.CharField(max_length=64)
    natural_key = models.CharField(max_length=512, db_index=True)
    values = models.JSONField(default=dict, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    prompt_version = models.CharField(max_length=64, blank=True, default="v1")

    class Meta:
        db_table = "admin_console_plan_record"
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(
                fields=("link", "natural_key"),
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_plan_record_link_key",
            )
        ]

    def __str__(self):
        return f"{self.plan_type}:{self.natural_key}"
