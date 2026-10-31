"""Cross-cutting resilience: retry, backoff, dead-lettering, per-link isolation."""

import pytest

from admin_console import services
from admin_console.models import CaptureSession, Link
from admin_console.tests import factories

pytestmark = pytest.mark.django_db


def _failing_then_ok(monkeypatch, failures):
    """Replace capture with one that fails ``failures`` times, then succeeds."""
    from admin_console import domtrack_client

    calls = {"n": 0}

    def capture_headless(url, duration_ms, nav_timeout_ms=None):
        calls["n"] += 1
        if calls["n"] <= failures:
            raise domtrack_client.DomtrackCaptureError("transient")
        return factories.make_trace_bytes(url=url)

    monkeypatch.setattr(domtrack_client.default_client, "capture_headless", capture_headless)
    return calls


def test_a_transient_failure_is_retried_and_then_succeeds(kept_link, monkeypatch,
                                                          no_retry_sleep):
    calls = _failing_then_ok(monkeypatch, failures=2)

    session = services.start_capture(kept_link)

    assert calls["n"] == 3
    assert session.state == CaptureSession.State.STORED
    kept_link.refresh_from_db()
    assert kept_link.pipeline_stage == Link.PipelineStage.CAPTURED
    assert kept_link.retry_count == 0
    assert kept_link.last_error == ""


def test_exhausted_retries_dead_letter_the_link(kept_link, monkeypatch, no_retry_sleep):
    calls = _failing_then_ok(monkeypatch, failures=99)

    with pytest.raises(Exception):
        services.start_capture(kept_link)

    assert calls["n"] == 3  # RETRY_MAX_ATTEMPTS
    kept_link.refresh_from_db()
    assert kept_link.pipeline_stage == Link.PipelineStage.DEAD_LETTERED
    assert kept_link.last_error == "transient"
    session = CaptureSession.objects.get(link=kept_link)
    assert session.state == CaptureSession.State.FAILED
    assert session.error == "transient"


def test_one_link_failing_does_not_block_another(kept_link, monkeypatch, no_retry_sleep,
                                                 stub_domtrack):
    other = Link.objects.create(
        site=kept_link.site,
        url="https://example.com/other",
        url_hash="other-hash",
        review_state=Link.ReviewState.KEPT,
        pipeline_stage=Link.PipelineStage.REFILTERED,
    )
    from admin_console import domtrack_client

    def capture_headless(url, duration_ms, nav_timeout_ms=None):
        if url == kept_link.url:
            raise domtrack_client.DomtrackCaptureError("only this link fails")
        return factories.make_trace_bytes(url=url)

    monkeypatch.setattr(domtrack_client.default_client, "capture_headless", capture_headless)

    with pytest.raises(Exception):
        services.start_capture(kept_link)

    session = services.start_capture(other)
    assert session.state == CaptureSession.State.STORED
    other.refresh_from_db()
    assert other.pipeline_stage == Link.PipelineStage.CAPTURED
    kept_link.refresh_from_db()
    assert kept_link.pipeline_stage == Link.PipelineStage.DEAD_LETTERED
