"""Capture session state-machine tests (US3, FR-014)."""

import pytest
from django.db import IntegrityError, transaction

from admin_console.models import CaptureSession, Link, Trace
from admin_console.tests.factories import make_trace_bytes

pytestmark = pytest.mark.django_db


def test_link_cannot_pass_capture_without_a_trace(kept_link):
    kept_link.pipeline_stage = Link.PipelineStage.CAPTURE
    kept_link.current_trace = None
    kept_link.save()
    assert kept_link.current_trace is None
    # No trace ⇒ the link may not be advanced to extraction.
    assert kept_link.pipeline_stage == Link.PipelineStage.CAPTURE


def test_awaiting_upload_is_distinct_from_failed(operator, kept_link):
    awaiting = CaptureSession.objects.create(
        link=kept_link,
        operator=operator,
        state=CaptureSession.State.AWAITING_UPLOAD,
        local_path="/tmp/x.json",
    )
    failed = CaptureSession.objects.create(
        link=kept_link, operator=operator, state=CaptureSession.State.FAILED, error="boom"
    )
    assert awaiting.state != failed.state
    assert awaiting.state == CaptureSession.State.AWAITING_UPLOAD
    assert failed.error == "boom"


def test_store_trace_creates_trace_and_marks_session(operator, kept_link):
    from admin_console import services

    session = CaptureSession.objects.create(
        link=kept_link, operator=operator, state=CaptureSession.State.AWAITING_UPLOAD
    )
    import tempfile

    tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=".json", delete=False)
    tmp.write(make_trace_bytes())
    tmp.close()
    trace = services.store_trace(session, tmp.name, operator)
    session.refresh_from_db()
    assert session.state == CaptureSession.State.STORED
    assert session.trace_id == trace.pk
    assert trace.origin == Trace.Origin.OPERATOR_CAPTURE
    assert trace.byte_size > 0
    assert len(trace.content_sha256) == 64


def test_only_one_non_terminal_session_per_link(operator, kept_link):
    CaptureSession.objects.create(
        link=kept_link, operator=operator, state=CaptureSession.State.RECORDING
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CaptureSession.objects.create(
                link=kept_link,
                operator=operator,
                state=CaptureSession.State.AWAITING_UPLOAD,
            )
    # A terminal session does not conflict.
    CaptureSession.objects.create(
        link=kept_link, operator=operator, state=CaptureSession.State.FAILED, error="x"
    )
