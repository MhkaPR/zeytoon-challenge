"""US5 — table extraction endpoint (FR-020..FR-022)."""

import pytest

from admin_console.models import ExtractedTable, ExtractedTableColumn, Link

pytestmark = pytest.mark.django_db


def test_extraction_persists_tables_with_domtrack_metadata(operator_client, traced_link):
    response = operator_client.post(f"/api/v1/ops/links/{traced_link.pk}/extractions")

    assert response.status_code == 201
    assert response.json()["extraction"]["table_count"] >= 1
    table = ExtractedTable.objects.get(link=traced_link)
    column = ExtractedTableColumn.objects.filter(table=table).first()
    assert column.path
    assert column.atype
    assert table.row_count >= 2
    traced_link.refresh_from_db()
    assert traced_link.pipeline_stage == Link.PipelineStage.EXTRACTED


def test_tables_endpoint_lists_columns_and_rows(operator_client, traced_link):
    operator_client.post(f"/api/v1/ops/links/{traced_link.pk}/extractions")

    response = operator_client.get(f"/api/v1/ops/links/{traced_link.pk}/tables")

    assert response.status_code == 200
    table = response.json()["tables"][0]
    assert table["columns"]
    assert table["rows"]
    assert set(table["rows"][0]) == {c["column_id"] for c in table["columns"]}


def test_empty_extraction_records_no_tables_and_flags(operator_client, traced_link,
                                                      stub_domtrack):
    stub_domtrack.table_result = {"total_candidates": 0, "tables_returned": 0, "tables": []}

    response = operator_client.post(f"/api/v1/ops/links/{traced_link.pk}/extractions")

    assert response.status_code == 200
    assert response.json()["extraction"]["table_count"] == 0
    assert ExtractedTable.objects.filter(link=traced_link).count() == 0
    traced_link.refresh_from_db()
    assert traced_link.pipeline_stage == Link.PipelineStage.FLAGGED
