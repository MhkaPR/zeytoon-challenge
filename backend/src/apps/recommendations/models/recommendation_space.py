"""Persisted recommendation plan space (source of truth; Redis is a cache).

The fitted space used to live only in Redis. It is now stored here so it
survives cache eviction and restarts. ``PlanSpaceProvider`` reads it through a
Redis read-through cache derived from this row.
"""

from django.db import models

from apps.utils.models import TimestampedModel


class RecommendationSpace(TimestampedModel):
    """One fitted version of the plan space.

    Exactly one row is active at a time; a refresh writes a new version,
    activates it, and deactivates the previous one.
    """

    version = models.CharField(max_length=128, unique=True)
    names = models.JSONField(default=list)
    values = models.JSONField(default=list)
    masks = models.JSONField(default=list)
    scales = models.JSONField(default=dict)
    plan_ids = models.JSONField(default=list)
    published_at = models.JSONField(default=list)
    raw_values = models.JSONField(default=dict)
    is_active = models.BooleanField(default=False, db_index=True)
    plan_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("is_active",),
                condition=models.Q(is_active=True, deleted_at__isnull=True),
                name="uniq_active_recommendation_space",
            ),
        ]

    def __str__(self):
        state = "active" if self.is_active else "inactive"
        return f"RecommendationSpace({self.version}, {state})"
