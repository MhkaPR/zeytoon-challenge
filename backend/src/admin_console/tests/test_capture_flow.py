"""Capture flow contract tests (US3, FR-012..FR-017, SC-007)."""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from admin_console.models import CaptureSession, Link, Trace
from admin_console.tests.factories import make_trace_bytes

pytestmark = pytest.mark.django_db


def _mock_capture(monkeypatch, path="/tmp/op/trace.json"):
    from admin_console import domtrack_client

    monkeypatch.setattr(
        domtrack_client,
        "start_local_capture",
        lambda url, mode="interactive", duration_ms=None, selector=None: {
            "json_path": path,
            "mutation_count": 3,
            "event_count": 2,
        },
    )


def test_capture_start_for_kept_link(operator_client, kept_link, monkeypatch):
    _mock_capture(monkeypatch)
    response = operator_client.post(
        f"/api/v1/ops/links/{kept_link.pk}/captures",
        {"mode": "interactive"},
        format="json",
    )
    assert response.status_code == 201
    body = response.json()["capture"]
    assert body["state"] == "awaiting_upload"
    assert body["local_path"] == "/tmp/op/trace.json"


def test_capture_start_for_non_kept_link_is_400(operator_client, site, monkeypatch):
    _mock_capture(monkeypatch)
    candidate = Link.objects.create(
        site=site, url="https://example.com/c", url_hash="c", source=Link.Source.SITEMAP
    )
    response = operator_client.post(
        f"/api/v1/ops/links/{candidate.pk}/captures", {"mode": "interactive"}, format="json"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "link_not_ready"


def test_domtrack_unreachable_returns_502_and_no_advance(operator_client, kept_link, monkeypatch):
    from admin_console import domtrack_client

    def _boom(*args, **kwargs):
        raise domtrack_client.DomtrackUnreachable("connection refused")

    monkeypatch.setattr(domtrack_client, "start_local_capture", _boom)
    response = operator_client.post(
        f"/api/v1/ops/links/{kept_link.pk}/captures", {"mode": "interactive"}, format="json"
    )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "domtrack_unreachable"
    kept_link.refresh_from_db()
    assert kept_link.current_trace is None
    session = CaptureSession.objects.get(link=kept_link)
    assert session.state == CaptureSession.State.FAILED


def test_trace_upload_stores_valid_trace_and_advances(operator_client, kept_link, monkeypatch):
    _mock_capture(monkeypatch)
    start = operator_client.post(
        f"/api/v1/ops/links/{kept_link.pk}/captures", {"mode": "interactive"}, format="json"
    )
    session_id = start.json()["capture"]["id"]

    upload = SimpleUploadedFile(
        "trace.json", make_trace_bytes(), content_type="application/json"
    )
    response = operator_client.post(
        f"/api/v1/ops/captures/{session_id}/trace", {"file": upload}, format="multipart"
    )
    assert response.status_code == 201
    trace = Trace.objects.get(link=kept_link)
    assert trace.is_valid_trace is True
    assert trace.captured_by_id is not None
    assert trace.storage_key.startswith("traces/")
    kept_link.refresh_from_db()
    assert kept_link.current_trace_id == trace.pk
    assert kept_link.pipeline_stage == Link.PipelineStage.CAPTURE
    session = CaptureSession.objects.get(pk=session_id)
    assert session.state == CaptureSession.State.STORED


def test_invalid_trace_is_rejected(operator_client, kept_link, monkeypatch):
    _mock_capture(monkeypatch)
    start = operator_client.post(
        f"/api/v1/ops/links/{kept_link.pk}/captures", {"mode": "interactive"}, format="json"
    )
    session_id = start.json()["capture"]["id"]
    upload = SimpleUploadedFile("bad.json", b"not a trace", content_type="application/json")
    response = operator_client.post(
        f"/api/v1/ops/captures/{session_id}/trace", {"file": upload}, format="multipart"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_field"
    assert not Trace.objects.filter(link=kept_link).exists()


def test_capture_fail_endpoint(operator_client, kept_link, monkeypatch):
    _mock_capture(monkeypatch)
    start = operator_client.post(
        f"/api/v1/ops/links/{kept_link.pk}/captures", {"mode": "interactive"}, format="json"
    )
    session_id = start.json()["capture"]["id"]
    response = operator_client.post(
        f"/api/v1/ops/captures/{session_id}/fail", {"error": "operator cancelled"}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["capture"]["state"] == "failed"
