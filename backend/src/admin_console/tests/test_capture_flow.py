"""US4 — server-side headless capture endpoint (FR-016..FR-019, SC-009)."""

import pytest

from admin_console import domtrack_client
from admin_console.models import CaptureSession, Link, Trace

pytestmark = pytest.mark.django_db


@pytest.fixture
def candidate_link(site):
    return Link.objects.create(
        site=site,
        url="https://example.com/plans",
        url_hash="candidate-hash",
        review_state=Link.ReviewState.CANDIDATE,
        pipeline_stage=Link.PipelineStage.DISCOVERED,
    )


def test_capture_stores_a_headless_trace(operator_client, kept_link, stub_domtrack):
    response = operator_client.post(
        f"/api/v1/ops/links/{kept_link.pk}/captures", {}, format="json"
    )

    assert response.status_code == 201
    body = response.json()
    assert body["capture_session"]["state"] == CaptureSession.State.STORED
    assert body["capture_session"]["mode"] == CaptureSession.Mode.HEADLESS_FIXED
    assert body["link"]["pipeline_stage"] == Link.PipelineStage.CAPTURED
    trace = Trace.objects.get(link=kept_link)
    assert trace.is_valid_trace is True
    assert trace.storage_key.startswith("traces/")
    assert stub_domtrack.capture_calls[0]["url"] == kept_link.url


def test_capture_refuses_a_non_kept_link(
    operator_client, candidate_link, stub_domtrack
):
    response = operator_client.post(
        f"/api/v1/ops/links/{candidate_link.pk}/captures", {}, format="json"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "link_not_ready"
    assert CaptureSession.objects.count() == 0


def test_capture_failure_is_dead_lettered(
    operator_client, kept_link, stub_domtrack, no_retry_sleep
):
    stub_domtrack.capture_error = domtrack_client.DomtrackCaptureError("boom")

    response = operator_client.post(
        f"/api/v1/ops/links/{kept_link.pk}/captures", {}, format="json"
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "dead_lettered"
    session = CaptureSession.objects.get(link=kept_link)
    assert session.state == CaptureSession.State.FAILED
    kept_link.refresh_from_db()
    assert kept_link.pipeline_stage == Link.PipelineStage.DEAD_LETTERED


def test_extraction_without_a_trace_is_refused(operator_client, kept_link):
    response = operator_client.post(f"/api/v1/ops/links/{kept_link.pk}/extractions")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "trace_required"
