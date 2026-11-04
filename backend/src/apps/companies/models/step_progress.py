"""Per-company registration step state."""

from django.db import models
from apps.utils.models import TimestampedModel
from apps.companies.models.company import Company


class CompanyStepProgress(TimestampedModel):
    """Per-company registration step state and locking (FR-007, FR-008, FR-010)."""

    class State(models.TextChoices):
        LOCKED = "locked", "Locked"
        OPEN = "open", "Open"
        SAVED = "saved", "Saved"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="step_progress"
    )
    step_key = models.CharField(max_length=64)
    order = models.PositiveSmallIntegerField()
    state = models.CharField(max_length=16, choices=State.choices, default=State.LOCKED)
    last_saved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "companies_step_progress"
        ordering = ("order",)
        constraints = [
            models.UniqueConstraint(
                fields=("company", "step_key"),
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_company_step_key",
            )
        ]
