"""Extracted tables, columns, and rows."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel
from apps.admin_console.models.table import ExtractedTable
from apps.admin_console.models.link import Link
from apps.admin_console.models.trace import Trace


class ExtractedTable(TimestampedModel):
    """A table document domtrack discovered in a trace (FR-020)."""

    trace = models.ForeignKey(
        Trace, on_delete=models.CASCADE, related_name="extracted_tables"
    )
    link = models.ForeignKey(
        Link, on_delete=models.CASCADE, related_name="extracted_tables"
    )
    table_index = models.PositiveIntegerField(default=0)
    parent = models.CharField(max_length=512, blank=True, default="")
    score = models.FloatField(default=0.0)
    column_count = models.PositiveIntegerField(default=0)
    row_count = models.PositiveIntegerField(default=0)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "admin_console_extracted_table"
        ordering = ("-score", "id")

    def __str__(self):
        return f"table {self.pk} ({self.row_count}x{self.column_count})"


class ExtractedTableColumn(TimestampedModel):
    """A column of an extracted table; ``path`` is domtrack's selector (diagnostics)."""

    table = models.ForeignKey(
        ExtractedTable, on_delete=models.CASCADE, related_name="columns"
    )
    column_id = models.CharField(max_length=128)
    label = models.CharField(max_length=512, blank=True, default="")
    path = models.CharField(max_length=1024, db_index=True)
    atype = models.CharField(max_length=64, blank=True, default="")
    slot = models.CharField(max_length=64, blank=True, default="")
    coverage = models.FloatField(default=0.0)
    row_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "admin_console_extracted_column"
        ordering = ("id",)

    def __str__(self):
        return f"{self.column_id}: {self.path}"


class ExtractedTableRow(TimestampedModel):
    """A row of an extracted table; ``cells`` maps column_id -> value (FR-020)."""

    table = models.ForeignKey(
        ExtractedTable, on_delete=models.CASCADE, related_name="rows"
    )
    row_index = models.PositiveIntegerField()
    cells = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "admin_console_extracted_row"
        ordering = ("row_index",)
        constraints = [
            models.UniqueConstraint(
                fields=("table", "row_index"),
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_extracted_row_table_index",
            )
        ]
