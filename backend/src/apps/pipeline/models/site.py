"""Crawl target for an approved company."""

from django.conf import settings
from django.db import models
from apps.utils.models import TimestampedModel


class Site(TimestampedModel):
    """The single crawl target for an approved company (FR-007).

    The domain is the adaptive-crawl seed; there is no sitemap state.
    """

    class MaintenanceState(models.TextChoices):
        ONBOARDING = "onboarding", "Onboarding"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    company = models.OneToOneField(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="ops_site",
    )
    domain = models.CharField(max_length=255, db_index=True)
    maintenance_state = models.CharField(
        max_length=16,
        choices=MaintenanceState.choices,
        default=MaintenanceState.ONBOARDING,
    )
    onboarded_at = models.DateTimeField(null=True, blank=True)
    last_discovered_at = models.DateTimeField(null=True, blank=True)
    last_replay_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "admin_console_site"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.domain} ({self.maintenance_state})"
