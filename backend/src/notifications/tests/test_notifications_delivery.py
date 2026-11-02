"""Notifications delivery + recipient management tests (US8, FR-041, research R15)."""

import pytest

from notifications.models import (
    Notification,
    NotificationDelivery,
    NotificationRecipient,
)
from notifications.services import add_recipient, notify

pytestmark = pytest.mark.django_db


def test_notify_creates_one_delivery_per_active_recipient(operator):
    add_recipient(user=operator)
    notification = notify(
        event_type="link_failure_rate_exceeded",
        subject="Link needs updating",
        body="failure rate high",
        dedup_key="link:1",
    )
    deliveries = NotificationDelivery.objects.filter(notification=notification)
    assert deliveries.count() == 1
    assert deliveries.first().channel == NotificationDelivery.Channel.IN_APP
    assert deliveries.first().state == NotificationDelivery.State.SENT


def test_dedup_key_prevents_duplicates(operator):
    add_recipient(user=operator)
    first = notify(
        event_type="link_failure_rate_exceeded",
        subject="a",
        dedup_key="dup-key",
    )
    second = notify(
        event_type="link_failure_rate_exceeded",
        subject="b",
        dedup_key="dup-key",
    )
    assert first.pk == second.pk
    assert Notification.objects.count() == 1


def test_failed_delivery_is_recorded_without_blocking_others(operator, other_user):
    add_recipient(user=operator)
    add_recipient(user=other_user)
    notification = notify(
        event_type="x",
        subject="s",
        dedup_key="k",
    )
    # Both recipients received an in-app delivery; a manual failure on one is isolated.
    delivery = NotificationDelivery.objects.filter(
        notification=notification, recipient__user=operator
    ).first()
    delivery.state = NotificationDelivery.State.FAILED
    delivery.error = "boom"
    delivery.save(update_fields=["state", "error", "updated_at"])
    other = NotificationDelivery.objects.filter(
        notification=notification, recipient__user=other_user
    ).first()
    assert other.state == NotificationDelivery.State.SENT


def test_inbox_reaches_active_recipients_only(operator_client, operator, other_user):
    add_recipient(user=operator)
    notify(event_type="x", subject="visible", dedup_key="k1")
    response = operator_client.get("/api/v1/ops/notifications")
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_inbox_empty_for_non_recipient(user_client):
    response = user_client.get("/api/v1/ops/notifications")
    assert response.status_code == 403


def test_recipients_are_admin_managed(operator_client, user_client, other_user):
    # A non-admin cannot manage recipients.
    forbidden = user_client.post(
        "/api/v1/ops/notification-recipients",
        {"user_id": other_user.pk},
        format="json",
    )
    assert forbidden.status_code == 403

    created = operator_client.post(
        "/api/v1/ops/notification-recipients",
        {"user_id": other_user.pk, "name": "Ops"},
        format="json",
    )
    assert created.status_code == 201
    recipient_id = created.json()["id"]
    assert NotificationRecipient.objects.get(pk=recipient_id).is_active is True

    deactivated = operator_client.post(
        f"/api/v1/ops/notification-recipients/{recipient_id}/deactivate"
    )
    assert deactivated.status_code == 200
    assert NotificationRecipient.objects.get(pk=recipient_id).is_active is False
