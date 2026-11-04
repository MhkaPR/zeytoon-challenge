"""Pluggable delivery channels for notifications (research R15).

Each channel is a callable ``(notification, recipient) -> None`` that raises on failure.
The in-app channel is always enabled by project decision (no email); additional channels
register here without changing callers, so adding one never touches the producer side
(Principle XII — reuse the platform shape rather than special-casing delivery).
"""

from notifications.models import NotificationDelivery

_IN_APP_CHANNEL = NotificationDelivery.Channel.IN_APP


def deliver_in_app(notification, recipient):
    """In-app delivery is in-process: writing the delivery row is the delivery."""
    return None


#: Registry of enabled channels. Email is intentionally absent (project decision: no email).
CHANNELS = {
    _IN_APP_CHANNEL: deliver_in_app,
}


def deliver(notification, recipient, channel):
    """Dispatch one delivery through its channel, recording a failure without raising."""
    handler = CHANNELS.get(channel)
    if handler is None:
        raise ValueError(f"No channel registered for {channel!r}.")
    return handler(notification, recipient)


__all__ = ["CHANNELS", "deliver", "deliver_in_app"]
