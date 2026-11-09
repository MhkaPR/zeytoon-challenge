"""CHK034 / FR-065: a referenced record cannot be soft-deleted."""

import pytest

from apps.utils.models import SoftDeleteConflict

pytestmark = pytest.mark.django_db


def test_soft_delete_is_refused_while_a_required_relation_exists(extracted_link):
    table = extracted_link.extracted_tables.first()

    with pytest.raises(SoftDeleteConflict):
        table.delete()

    table.refresh_from_db()
    assert table.deleted_at is None
    assert table.rows.exists()
