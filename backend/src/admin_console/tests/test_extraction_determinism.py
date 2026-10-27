"""Extraction determinism test (US4, FR-019, SC-008)."""

import pytest

from admin_console.models import ExtractedTable
from admin_console.services import extract_tables_for_link

pytestmark = pytest.mark.django_db


def _snapshot(link):
    tables = []
    for table in ExtractedTable.objects.filter(link=link).order_by("table_index"):
        tables.append(
            {
                "columns": [
                    (c.column_id, c.path, c.atype, c.coverage)
                    for c in table.columns.all()
                ],
                "rows": [
                    (r.row_index, tuple(sorted(r.cells.items())))
                    for r in table.rows.all()
                ],
            }
        )
    return tables


def test_extracting_twice_replaces_and_is_identical(traced_link):
    extract_tables_for_link(traced_link)
    first = _snapshot(traced_link)
    assert first
    extract_tables_for_link(traced_link)
    second = _snapshot(traced_link)
    assert first == second
    # No duplicate accumulation from a re-run.
    assert ExtractedTable.objects.filter(link=traced_link).count() == len(first)
