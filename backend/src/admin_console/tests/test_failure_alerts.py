"""Failure-rate and alerting tests (US8, FR-040, SC-013)."""

import pytest
from constance.test import override_config

from admin_console.models import FailureAlert, Link
from admin_console.services import evaluate_failure_alert
from notifications.models import Notification

pytestmark = pytest.mark.django_db


def _set_rate(link, rate):
    link.failure_rate = rate
    link.save(update_fields=["failure_rate", "updated_at"])
    return link


@override_config(FAILURE_RATE_THRESHOLD=0.5)
def test_crossing_threshold_creates_exactly_one_open_alert(published_link, operator):
    from notifications.services import add_recipient

    add_recipient(user=operator)
    _set_rate(published_link, 0.8)
    alert = evaluate_failure_alert(published_link)
    assert alert is not None
    assert alert.state == FailureAlert.State.OPEN
    assert FailureAlert.objects.filter(link=published_link, state="open").count() == 1
    # A notification names the link and carries the dedup key.
    notification = Notification.objects.get(event_type="link_failure_rate_exceeded")
    assert published_link.url in notification.subject
    assert notification.dedup_key == alert.notification_dedup_key


@override_config(FAILURE_RATE_THRESHOLD=0.5)
def test_alert_not_repeated_while_open(published_link):
    _set_rate(published_link, 0.8)
    evaluate_failure_alert(published_link)
    evaluate_failure_alert(published_link)
    evaluate_failure_alert(published_link)
    assert FailureAlert.objects.filter(link=published_link).count() == 1
    assert Notification.objects.filter(event_type="link_failure_rate_exceeded").count() == 1


@override_config(FAILURE_RATE_THRESHOLD=0.5)
def test_recovery_resolves_and_re_crossing_opens_a_new_alert(published_link):
    _set_rate(published_link, 0.8)
    first = evaluate_failure_alert(published_link)
    # Rate falls back below threshold -> resolved.
    _set_rate(published_link, 0.1)
    evaluate_failure_alert(published_link)
    first.refresh_from_db()
    assert first.state == FailureAlert.State.RESOLVED
    assert Notification.objects.filter(is_resolved=True).exists()

    # A later re-crossing opens a fresh alert.
    _set_rate(published_link, 0.9)
    second = evaluate_failure_alert(published_link)
    assert second.pk != first.pk
    assert second.state == FailureAlert.State.OPEN
    assert FailureAlert.objects.filter(link=published_link).count() == 2


@override_config(FAILURE_RATE_THRESHOLD=0.5)
def test_below_threshold_with_no_open_alert_is_noop(published_link):
    _set_rate(published_link, 0.2)
    assert evaluate_failure_alert(published_link) is None
    assert FailureAlert.objects.count() == 0
