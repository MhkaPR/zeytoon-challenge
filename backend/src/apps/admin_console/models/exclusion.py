"""Operator plan exclusions."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel
from apps.admin_console.models.link import Link


class PlanExclusion(TimestampedModel):
    """Operator decision to keep a logical plan out across future extractions."""

    link = models.ForeignKey(
        Link, on_delete=models.CASCADE, related_name="plan_exclusions"
    )
    fingerprint = models.CharField(max_length=64)
    plan_type = models.CharField(max_length=64)
    plan_name = models.CharField(max_length=255)
    price_amount = models.CharField(max_length=64)

    class Meta:
        db_table = "admin_console_plan_exclusion"
        constraints = [
            models.UniqueConstraint(
                fields=("link", "fingerprint"),
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_plan_exclusion_link_fingerprint",
            )
        ]
