"""Fold an anonymous device profile into an account at sign-in."""

from __future__ import annotations

from django.db import transaction

from apps.recommendations.models import InterestProfile


class StateMerger:
    """Merges device state into an account inside one transaction."""

    @staticmethod
    def merge_on_login(user, visitor_id):
        if not visitor_id or user is None or not getattr(user, "pk", None):
            return None
        with transaction.atomic():
            visitor = (
                InterestProfile.objects.select_for_update()
                .filter(visitor_id=visitor_id)
                .first()
            )
            if visitor is None:
                return None
            account = (
                InterestProfile.objects.select_for_update()
                .filter(user=user)
                .first()
            )
            if account is None:
                account = InterestProfile.objects.create(
                    user=user,
                    position=visitor.position,
                    uncertainty=visitor.uncertainty,
                    cluster_activity=visitor.cluster_activity,
                    space_version=visitor.space_version,
                    signal_count=visitor.signal_count,
                    last_signal_at=visitor.last_signal_at,
                )
            visitor.merged_into = user
            visitor.save(update_fields=("merged_into", "updated_at"))
            return account

    @staticmethod
    def clear_visitor(visitor_id):
        if not visitor_id:
            return 0
        return InterestProfile.objects.filter(visitor_id=visitor_id).delete()[0]
