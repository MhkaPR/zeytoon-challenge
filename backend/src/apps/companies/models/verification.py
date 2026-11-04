"""Append-only verification outcomes."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel
from apps.companies.models.company import Company
from apps.companies.models.append_only import _AppendOnlyMixin


class VerificationDecision(_AppendOnlyMixin, TimestampedModel):
    """One append-only verification outcome for a company (FR-016, FR-017)."""

    class Outcome(models.TextChoices):
        APPROVED = "approved", "Approved"
        NOT_APPROVED = "not_approved", "Not approved"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="verification_decisions"
    )
    outcome = models.CharField(max_length=16, choices=Outcome.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="verification_decisions"
    )
    decided_at = models.DateTimeField()
    note = models.TextField(blank=True, default="")

    class Meta:
        db_table = "companies_verification_decision"
        ordering = ("-decided_at",)
