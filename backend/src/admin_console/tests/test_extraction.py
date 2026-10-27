"""Extraction contract tests (US4, FR-018, FR-020, SC-007)."""

import pytest

from admin_console.models import ExtractedTable, Link

pytestmark = pytest.mark.django_db


def test_extraction_persists_tables_and_columns(operator_client, traced_link):
    response = operator_client.post(f"/api/v1/ops/links/{traced_link.pk}/extractions")
    assert response.status_code == 201
    body = response.json()
    assert body["table_count"] >= 1
    traced_link.refresh_from_db()
    assert traced_link.pipeline_stage == Link.PipelineStage.EXTRACTED
    table = ExtractedTable.objects.get(link=traced_link)
    columns = list(table.columns.all())
    assert columns
    for column in columns:
        assert column.path  # domtrack's selector
        assert column.atype
        assert 0.0 <= column.coverage <= 1.0
    assert table.rows.count() >= 3


def test_extraction_without_trace_is_409(operator_client, kept_link):
    response = operator_client.post(f"/api/v1/ops/links/{kept_link.pk}/extractions")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "trace_required"
    kept_link.refresh_from_db()
    assert kept_link.pipeline_stage == Link.PipelineStage.CAPTURE


def test_extraction_with_no_tables_flags_link(operator_client, traced_link):
    from django.utils import timezone

    from admin_console import artifacts
    from admin_console.models import Trace
    from admin_console.tests.factories import make_trace_bytes

    data = make_trace_bytes(rows=[], url=traced_link.url)
    key, backend, size, digest = artifacts.save_trace(data)
    trace = Trace.objects.create(
        link=traced_link,
        captured_at=timezone.now(),
        storage_key=key,
        storage_backend=backend,
        byte_size=size,
        content_sha256=digest,
        is_valid_trace=True,
    )
    traced_link.current_trace = trace
    traced_link.save(update_fields=["current_trace", "updated_at"])

    response = operator_client.post(f"/api/v1/ops/links/{traced_link.pk}/extractions")
    body = response.json()
    assert body["table_count"] == 0
    traced_link.refresh_from_db()
    assert traced_link.pipeline_stage == Link.PipelineStage.FLAGGED


def test_tables_endpoint_returns_columns_and_rows(operator_client, traced_link):
    operator_client.post(f"/api/v1/ops/links/{traced_link.pk}/extractions")
    response = operator_client.get(f"/api/v1/ops/links/{traced_link.pk}/tables")
    assert response.status_code == 200
    body = response.json()
    assert body["tables"]
    table = body["tables"][0]
    assert "columns" in table and "rows" in table
