"""Append-only record of one interaction that shaped a preference profile."""

from django.db import models

from apps.recommendations.models.interest_profile import InterestProfile
from apps.utils.models import TimestampedModel


class InterestSignal(TimestampedModel):
    """One recorded interaction attributed to one interest profile."""

    class Kind(models.TextChoices):
        DESTINATION_VISIT = "destination_visit", "Destination visit"
        DETAILS_VIEW = "details_view", "Details view"
        SEARCH_IMPRESSION = "search_impression", "Search impression"

    profile = models.ForeignKey(
        InterestProfile,
        on_delete=models.CASCADE,
        related_name="signals",
    )
    kind = models.CharField(max_length=32, choices=Kind.choices, db_index=True)
    plan_ids = models.JSONField(default=list, blank=True)
    query = models.CharField(max_length=255, blank=True, default="")
    weight = models.FloatField(default=0.0)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("profile", "-created_at")),
            models.Index(fields=("kind",)),
        ]

    def __str__(self):
        return f"InterestSignal({self.kind}, profile={self.profile_id})"
