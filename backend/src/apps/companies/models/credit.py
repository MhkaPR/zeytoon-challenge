"""Append-only credit ledger records."""

from django.contrib.auth import get_user_model
from django.db import models
from apps.utils.models import TimestampedModel
from apps.companies.models.company import Company
from apps.companies.models.append_only import _AppendOnlyMixin


class CreditLedgerEntry(_AppendOnlyMixin, TimestampedModel):
    """Historical, append-only credit entry retained for audit purposes."""

    class Direction(models.TextChoices):
        CHARGE = "charge", "Charge"
        DECHARGE = "decharge", "Decharge"

    class Reason(models.TextChoices):
        PAYMENT = "payment", "Payment"
        PLATFORM_VIEW = "platform_view", "Platform view"
        ADJUSTMENT = "adjustment", "Adjustment"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="credit_entries"
    )
    direction = models.CharField(max_length=16, choices=Direction.choices)
    amount = models.PositiveIntegerField()
    reason = models.CharField(max_length=32, choices=Reason.choices)
    reference = models.CharField(max_length=255, blank=True, default="")
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credit_entries",
    )

    class Meta:
        db_table = "companies_credit_ledger_entry"
        ordering = ("-created_at",)
