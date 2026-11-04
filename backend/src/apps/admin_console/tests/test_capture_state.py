"""US4 — capture session state machine (FR-053)."""

import pytest
from django.db import IntegrityError, transaction

from apps.admin_console import services
from apps.admin_console.models import CaptureSession, Link

pytestmark = pytest.mark.django_db


def test_successful_capture_ends_in_stored(kept_link, stub_domtrack):
    session = services.start_capture(kept_link)
    assert session.state == CaptureSession.State.STORED
    assert session.trace_id is not None


def test_a_second_session_while_recording_is_refused(kept_link, stub_domtrack):
    CaptureSession.objects.create(
        link=kept_link,
        mode=CaptureSession.Mode.HEADLESS_FIXED,
        state=CaptureSession.State.RECORDING,
        duration_ms=1000,
    )

    with pytest.raises(RuntimeError, match="capture_in_progress"):
        services.start_capture(kept_link)


def test_only_one_non_terminal_session_per_link_is_allowed(kept_link):
    CaptureSession.objects.create(
        link=kept_link,
        mode=CaptureSession.Mode.HEADLESS_FIXED,
        state=CaptureSession.State.RECORDING,
        duration_ms=1000,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CaptureSession.objects.create(
                link=kept_link,
                mode=CaptureSession.Mode.HEADLESS_FIXED,
                state=CaptureSession.State.PENDING,
                duration_ms=1000,
            )


def test_terminal_sessions_do_not_block_a_new_capture(kept_link, stub_domtrack):
    CaptureSession.objects.create(
        link=kept_link,
        mode=CaptureSession.Mode.HEADLESS_FIXED,
        state=CaptureSession.State.FAILED,
        duration_ms=1000,
    )
    session = services.start_capture(kept_link)
    assert session.state == CaptureSession.State.STORED


def test_fail_capture_marks_failed(kept_link):
    session = CaptureSession.objects.create(
        link=kept_link,
        mode=CaptureSession.Mode.HEADLESS_FIXED,
        state=CaptureSession.State.RECORDING,
        duration_ms=1000,
    )
    services.fail_capture(session, "navigation_timeout")
    session.refresh_from_db()
    assert session.state == CaptureSession.State.FAILED
    assert session.error == "navigation_timeout"
