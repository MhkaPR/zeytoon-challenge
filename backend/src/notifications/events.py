"""Structured, masked event logging for the notifications app (FR-044)."""

import logging

logger = logging.getLogger(__name__)


def _emit(event, **extra):
    payload = {"event": event}
    payload.update(extra)
    logger.info(event, extra=payload)


def notification_created(notification):
    _emit(
        "notification_created",
        event_type=notification.event_type,
        severity=notification.severity,
        notification_id=notification.pk,
        related_object=notification.related_object,
    )


def delivery_recorded(delivery):
    _emit(
        "notification_delivery",
        notification_id=delivery.notification_id,
        recipient_id=delivery.recipient_id,
        channel=delivery.channel,
        state=delivery.state,
    )
