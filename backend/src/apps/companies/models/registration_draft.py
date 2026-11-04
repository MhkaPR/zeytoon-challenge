"""Short-lived registration step drafts."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel
from apps.companies.models.company import Company


class CompanyRegistrationDraft(TimestampedModel):
    """Short-lived input for a half-finished, unsubmitted step (FR-009).

    Not a domain record: abandoning a step deletes only that (owner, step) draft.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="company_registration_drafts"
    )
    step_key = models.CharField(max_length=64)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="registration_drafts",
    )
    payload = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "companies_registration_draft"
        ordering = ("-created_at",)
