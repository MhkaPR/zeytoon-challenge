"""US10 — failure rate and one-alert-per-crossing alerts (FR-044, SC-017)."""

import pytest

from apps.admin_console import services
from apps.pipeline.models import FailureAlert, ReplayRun
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db


def _runs(link, failed, succeeded):
    for _ in range(failed):
        ReplayRun.objects.create(link=link, state=ReplayRun.State.FAILED)
    for _ in range(succeeded):
        ReplayRun.objects.create(link=link, state=ReplayRun.State.SUCCEEDED)


def test_failure_rate_derives_from_the_replay_window(kept_link):
    _runs(kept_link, failed=3, succeeded=2)

    rate = services.recompute_failure_rate(kept_link)

    assert rate == pytest.approx(0.6)
    kept_link.refresh_from_db()
    assert kept_link.failure_rate == pytest.approx(0.6)


def test_crossing_the_threshold_opens_exactly_one_alert(
    kept_link, notification_recipient
):
    _runs(kept_link, failed=3, succeeded=2)

    services.recompute_failure_rate(kept_link)
    services.recompute_failure_rate(kept_link)

    assert (
        FailureAlert.objects.filter(
            link=kept_link, state=FailureAlert.State.OPEN
        ).count()
        == 1
    )
    notification = Notification.objects.get(event_type="link_failure_alert")
    assert str(kept_link.pk) in notification.related_object
    assert kept_link.url in notification.subject


def test_a_fall_resolves_the_alert(kept_link, notification_recipient):
    _runs(kept_link, failed=3, succeeded=2)
    services.recompute_failure_rate(kept_link)

    _runs(kept_link, failed=0, succeeded=5)
    services.recompute_failure_rate(kept_link)

    alert = FailureAlert.objects.get(link=kept_link)
    assert alert.state == FailureAlert.State.RESOLVED
    assert alert.resolved_at is not None


def test_a_later_rise_opens_a_new_alert(kept_link, notification_recipient):
    _runs(kept_link, failed=3, succeeded=2)
    services.recompute_failure_rate(kept_link)
    _runs(kept_link, failed=0, succeeded=5)
    services.recompute_failure_rate(kept_link)

    _runs(kept_link, failed=5, succeeded=0)
    services.recompute_failure_rate(kept_link)

    assert FailureAlert.objects.filter(link=kept_link).count() == 2
    assert (
        FailureAlert.objects.filter(
            link=kept_link, state=FailureAlert.State.OPEN
        ).count()
        == 1
    )
