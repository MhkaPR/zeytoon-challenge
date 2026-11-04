"""Company domain model."""

from django.contrib.auth import get_user_model
from django.db import models
from apps.utils.models import TimestampedModel


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
        from apps.companies.domain import normalize_domain

        normalized = normalize_domain(self.domain)
        if normalized:
            self.domain = normalized
        super().save(*args, **kwargs)
