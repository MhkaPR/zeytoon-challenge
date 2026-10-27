"""Labeling gate tests (US5, FR-021..FR-023, SC-016)."""

from unittest.mock import patch

import pytest
from constance.test import override_config

from admin_console.models import SemanticLabel
from admin_console.services import extract_tables_for_link, label_tables_for_link

pytestmark = pytest.mark.django_db


def _fake_labeled(tables, config):
    return {
        "tables_returned": len(tables),
        "tables": [
            {
                "meta": {"title": f"Table {i}", "purpose": "plans"},
                "columns": [
                    {"semantic_label": f"label-{c['id']}"} for c in table["columns"]
                ],
            }
            for i, table in enumerate(tables)
        ],
    }


def test_labeling_disabled_by_default_returns_403(operator_client, traced_link):
    extract_tables_for_link(traced_link)
    response = operator_client.post(f"/api/v1/ops/links/{traced_link.pk}/labeling")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "labeling_disabled"
    assert SemanticLabel.objects.count() == 0


@override_config(LABELING_ENABLED=True)
def test_enabled_labeling_persists_labels(traced_link):
    extract_tables_for_link(traced_link)
    with patch(
        "admin_console.domtrack_client.label_tables", side_effect=_fake_labeled
    ):
        result = label_tables_for_link(traced_link)
    assert result["labeled"] is True
    assert SemanticLabel.objects.count() > 0


@override_config(LABELING_ENABLED=True)
def test_pipeline_works_identically_with_and_without_labels(traced_link):
    extract_tables_for_link(traced_link)
    before = traced_link.pipeline_stage
    with patch(
        "admin_console.domtrack_client.label_tables", side_effect=_fake_labeled
    ):
        label_tables_for_link(traced_link)
    traced_link.refresh_from_db()
    # Labeling never changes the pipeline stage (FR-023).
    assert traced_link.pipeline_stage == before
