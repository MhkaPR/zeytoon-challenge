"""US5 — extraction is deterministic and replaces the previous result (FR-021, SC-010)."""

import pytest

from admin_console import services
from admin_console.models import ExtractedTable, ExtractedTableRow

pytestmark = pytest.mark.django_db


def _rows_snapshot(link):
    return [
        (table.table_index, row.row_index, tuple(sorted(row.cells.items())))
        for table in link.extracted_tables.all()
        for row in table.rows.all()
    ]


def test_re_extraction_replaces_and_matches(traced_link):
    services.extract_link_tables(traced_link)
    first_ids = list(ExtractedTable.objects.filter(link=traced_link).values_list("id", flat=True))
    first = _rows_snapshot(traced_link)

    services.extract_link_tables(traced_link)

    second_ids = list(ExtractedTable.objects.filter(link=traced_link).values_list("id", flat=True))
    assert set(first_ids).isdisjoint(second_ids)
    assert _rows_snapshot(traced_link) == first
    assert ExtractedTableRow.objects.filter(table__link=traced_link).count() > 0
