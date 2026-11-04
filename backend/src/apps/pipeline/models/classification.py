"""Rule-based table classification."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel


class TableClassification(TimestampedModel):
    """Rule-based decision that an extracted table contains price data."""

    table = models.OneToOneField(
        "pipeline.ExtractedTable", on_delete=models.CASCADE, related_name="classification"
    )
    is_price_table = models.BooleanField(default=False)
    matching_rows = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "admin_console_table_classification"
        ordering = ("-matching_rows", "id")

    def __str__(self):
        kind = "price table" if self.is_price_table else "not-price-table"
        return f"table {self.table_id}: {kind} ({self.matching_rows} matching rows)"
