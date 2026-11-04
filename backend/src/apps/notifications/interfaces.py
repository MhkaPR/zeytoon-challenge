"""Public interface for the notifications module (Constitution Principle V).

Producers raise notifications only through this interface; ``notifications`` never
imports its callers.
"""

from apps.notifications import services
from apps.notifications.models import Notification


class NotificationsInterface:
    """The single sanctioned entry point into the notifications module."""

    Severity = Notification.Severity

    @staticmethod
    def notify(**kwargs):
        return services.notify(**kwargs)

    @staticmethod
    def resolve_notifications(**kwargs):
        return services.resolve_notifications(**kwargs)


__all__ = ["NotificationsInterface"]
