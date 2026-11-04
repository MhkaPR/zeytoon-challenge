"""Company domain models.

Historical credit ledger records remain stored for audit, but the free service exposes no
credit or payment workflow.
"""

from django.contrib.auth import get_user_model
from django.db import models

from utils.models import TimestampedModel

User = get_user_model()


class Company(TimestampedModel):
    """A registrable business entity owned by exactly one user.

    Never hard-deleted (FR-039); deletion of the owner's account sets ``is_archived``.
    """

    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending verification"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"


    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="companies",
        db_index=True,
    )
    domain = models.CharField(max_length=255, db_index=True)
    company_name = models.CharField(max_length=255)
    representative_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=32)
    internal_number = models.CharField(max_length=32, blank=True, default="")

    verification_status = models.CharField(
        max_length=16,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    is_archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "companies_company"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.company_name} ({self.domain})"

    @property
    def is_verified(self):
        return self.verification_status == self.VerificationStatus.VERIFIED

    @property
    def is_unverified(self):
        return not self.is_verified

    def save(self, *args, **kwargs):
        """Normalize the domain on every save (FR-041)."""
        from companies.domain import normalize_domain

        normalized = normalize_domain(self.domain)
        if normalized:
            self.domain = normalized
        super().save(*args, **kwargs)


class _AppendOnlyMixin(models.Model):
    """Mixin making a model insert-only: existing rows cannot be updated or deleted."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk is not None and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError("This record is append-only and cannot be modified.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("This record is append-only and cannot be deleted.")


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
        User, on_delete=models.PROTECT, related_name="verification_decisions"
    )
    decided_at = models.DateTimeField()
    note = models.TextField(blank=True, default="")

    class Meta:
        db_table = "companies_verification_decision"
        ordering = ("-decided_at",)


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


class CompanyRegistrationDraft(TimestampedModel):
    """Short-lived input for a half-finished, unsubmitted step (FR-009).

    Not a domain record: abandoning a step deletes only that (owner, step) draft.
    """

    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="company_registration_drafts"
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
