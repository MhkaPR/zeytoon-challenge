"""Notification services: raising notifications and delivering them in-app.

Producers (e.g. ``admin_console`` replay) call :func:`notify`. Delivery is in-app only
(project decision: no email). Each notification produces one ``NotificationDelivery``
per active recipient on the in-app channel; a failed in-app delivery is recorded but
does not block others.
"""

from django.db import transaction
from django.utils import timezone

from apps.notifications import events
from apps.notifications.models import (
    Notification,
    NotificationDelivery,
    NotificationRecipient,
)


def active_recipients():
    return NotificationRecipient.objects.filter(is_active=True).select_related("user")


@transaction.atomic
def notify(
    *,
    event_type,
    subject,
    body="",
    severity=Notification.Severity.WARNING,
    related_object="",
    dedup_key="",
):
    """Create a notification (idempotent on ``dedup_key``) and deliver it in-app.

    A repeated publish with the same non-empty ``dedup_key`` returns the existing
    notification without creating another (FR-041).
    """
    if dedup_key:
        existing = Notification.objects.filter(dedup_key=dedup_key).first()
        if existing is not None:
            return existing

    notification = Notification.objects.create(
        event_type=event_type,
        severity=severity,
        subject=subject,
        body=body,
        related_object=related_object,
        dedup_key=dedup_key,
    )
    deliver(notification)
    events.notification_created(notification)
    return notification


def deliver(notification):
    """Create one in-app delivery per active recipient and mark it sent."""
    from apps.notifications import channels

    deliveries = []
    for recipient in active_recipients():
        delivery, created = NotificationDelivery.objects.get_or_create(
            notification=notification,
            recipient=recipient,
            channel=NotificationDelivery.Channel.IN_APP,
            defaults={"state": NotificationDelivery.State.PENDING},
        )
        if not created and delivery.state == NotificationDelivery.State.SENT:
            continue
        try:
            channels.deliver(
                notification, recipient, NotificationDelivery.Channel.IN_APP
            )
            delivery.state = NotificationDelivery.State.SENT
            delivery.sent_at = timezone.now()
            delivery.error = ""
        except Exception as exc:  # pragma: no cover - defensive, in-app is in-process
            delivery.state = NotificationDelivery.State.FAILED
            delivery.error = str(exc)[:255]
        delivery.save(update_fields=["state", "sent_at", "error", "updated_at"])
        deliveries.append(delivery)
        events.delivery_recorded(delivery)
    return deliveries


@transaction.atomic
def resolve_notifications(*, event_type, related_object=""):
    """Mark open notifications resolved (state-based, FR-040)."""
    now = timezone.now()
    return Notification.objects.filter(
        event_type=event_type, related_object=related_object, is_resolved=False
    ).update(is_resolved=True, resolved_at=now)


def add_recipient(*, user, name="", actor=None):
    """Add (or reactivate) a recipient. Only admins should call this (FR-041)."""
    recipient, created = NotificationRecipient.objects.get_or_create(
        user=user,
        defaults={"name": name, "created_by": actor, "is_active": True},
    )
    if not created:
        recipient.is_active = True
        if name:
            recipient.name = name
        recipient.save(update_fields=["is_active", "name", "updated_at"])
    return recipient


def deactivate_recipient(recipient):
    """Deactivate rather than erase, preserving delivered history (FR-041)."""
    recipient.is_active = False
    recipient.save(update_fields=["is_active", "updated_at"])
    return recipient


def inbox_for_user(user, limit=100):
    """Return the user's in-app notifications via their recipient deliveries (FR-041)."""
    if not NotificationRecipient.objects.filter(user=user, is_active=True).exists():
        return []
    notification_ids = NotificationDelivery.objects.filter(
        recipient__user=user,
        recipient__is_active=True,
        channel=NotificationDelivery.Channel.IN_APP,
    ).values_list("notification_id", flat=True)
    return list(
        Notification.objects.filter(pk__in=notification_ids).order_by("-created_at")[
            :limit
        ]
    )
