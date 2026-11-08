"""Per-viewer preference profile for related-plan ordering."""

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.utils.models import TimestampedModel


class InterestProfile(TimestampedModel):
    """Accumulated taste of one viewer.

    Exactly one owner link is set: an anonymous device (``visitor_id``) or an account
    (``user``). A device profile that has been folded into an account is tombstoned with
    ``merged_into`` so late signals are redirected instead of recreating an orphan.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="interest_profiles",
    )
    visitor_id = models.UUIDField(null=True, blank=True, db_index=True)
    position = models.JSONField(default=list, blank=True)
    uncertainty = models.JSONField(default=list, blank=True)
    cluster_activity = models.JSONField(default=list, blank=True)
    space_version = models.CharField(max_length=64, blank=True, default="")
    signal_count = models.PositiveIntegerField(default=0)
    last_signal_at = models.DateTimeField(null=True, blank=True, db_index=True)
    merged_into = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(user__isnull=False, visitor_id__isnull=True)
                    | Q(user__isnull=True, visitor_id__isnull=False)
                ),
                name="interest_profile_single_owner",
            ),
            models.UniqueConstraint(
                fields=("user",),
                condition=Q(deleted_at__isnull=True, user__isnull=False),
                name="uniq_active_interest_profile_user",
            ),
            models.UniqueConstraint(
                fields=("visitor_id",),
                condition=Q(deleted_at__isnull=True, visitor_id__isnull=False),
                name="uniq_active_interest_profile_visitor",
            ),
        ]

    def __str__(self):
        owner = f"user:{self.user_id}" if self.user_id else f"visitor:{self.visitor_id}"
        return f"InterestProfile({owner})"
