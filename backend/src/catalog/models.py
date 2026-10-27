"""Catalog-owned published plan records (spec 003 data-model.md, FR-034..FR-036).

``admin_console`` writes these rows only through :mod:`catalog.interfaces`; the ids it
passes for provenance (``site``/``link``/``trace``/``recipe``) are opaque integers, so
``catalog`` never imports ``admin_console`` internals (Constitution Principle V).
"""

from django.db import models

from utils.models import TimestampedModel


class PublishedRecord(TimestampedModel):
    """A cleaned, filterable plan record placed on the main site."""

    site = models.IntegerField(db_index=True)
    link = models.IntegerField(db_index=True)
    trace = models.IntegerField(db_index=True)
    recipe = models.IntegerField(db_index=True)
    source = models.CharField(max_length=64, default="admin_console")
    plan_type = models.CharField(max_length=64, db_index=True)
    natural_key = models.CharField(max_length=512, db_index=True)
    values = models.JSONField(default=dict, blank=True)
    cleaning_exceptions = models.JSONField(default=dict, blank=True)
    is_published = models.BooleanField(default=True, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    retired_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "catalog_published_record"
        ordering = ("-published_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("source", "site", "natural_key"),
                name="uniq_published_record_source_site_key",
            )
        ]

    def __str__(self):
        return f"{self.plan_type}:{self.natural_key}"
