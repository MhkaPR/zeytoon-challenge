"""Publishing tests (US7, FR-030, FR-034..FR-036, SC-009)."""

import pytest

from admin_console.models import Link
from catalog.models import PublishedRecord

pytestmark = pytest.mark.django_db


def _publish_ready_link(operator_client, traced_link):
    """Extract tables, save a complete hosting recipe, and return the link + tables."""
    operator_client.post(f"/api/v1/ops/links/{traced_link.pk}/extractions")
    tables = operator_client.get(f"/api/v1/ops/links/{traced_link.pk}/tables").json()[
        "tables"
    ]
    table = tables[0]
    column = dict(table["columns"][0])
    required = (
        "plan_name",
        "storage_amount",
        "storage_unit",
        "ram_amount",
        "cpu_cores",
        "bandwidth_amount",
        "price_amount",
        "billing_period",
    )
    bindings = [
        {
            "schema_field_key": key,
            "source_table_id": table["id"],
            "source_column_id": column["id"],
            "selector": column["path"],
            "formula": "",
        }
        for key in required
    ]
    response = operator_client.put(
        f"/api/v1/ops/links/{traced_link.pk}/recipe",
        {"plan_type": "hosting", "bindings": bindings},
        format="json",
    )
    assert response.status_code == 200
    traced_link.refresh_from_db()
    return traced_link, table, column


def test_publish_writes_catalog_records_with_provenance(
    operator_client, traced_link
):
    link, table, column = _publish_ready_link(operator_client, traced_link)
    response = operator_client.post(f"/api/v1/ops/links/{link.pk}/publish")
    assert response.status_code == 200
    assert response.json()["published"] == table["row_count"]

    link.refresh_from_db()
    assert link.pipeline_stage == Link.PipelineStage.PUBLISHED

    records = PublishedRecord.objects.filter(site=link.site_id, link=link.pk)
    assert records.count() == table["row_count"]
    record = records.first()
    recipe = link.recipes.get(is_current=True)
    assert record.trace == link.current_trace_id
    assert record.recipe == recipe.pk
    assert record.source == "admin_console"
    assert record.plan_type == "hosting"
    assert record.is_published is True
    assert record.values.get("plan_name")


def test_publish_upserts_by_source_site_natural_key(operator_client, traced_link):
    link, table, _column = _publish_ready_link(operator_client, traced_link)
    operator_client.post(f"/api/v1/ops/links/{link.pk}/publish")
    first_count = PublishedRecord.objects.filter(site=link.site_id).count()
    # Re-publishing updates the same rows rather than duplicating (FR-035).
    operator_client.post(f"/api/v1/ops/links/{link.pk}/publish")
    assert PublishedRecord.objects.filter(site=link.site_id).count() == first_count


def test_removed_item_is_retired_not_stale(operator_client, traced_link):
    from catalog.interfaces import CatalogInterface

    link, table, _column = _publish_ready_link(operator_client, traced_link)
    operator_client.post(f"/api/v1/ops/links/{link.pk}/publish")
    record = PublishedRecord.objects.filter(site=link.site_id).first()

    CatalogInterface.retire_published_record(site=link.site_id, natural_key=record.natural_key)
    record.refresh_from_db()
    assert record.is_published is False
    assert record.retired_at is not None


def test_publish_without_complete_recipe_is_409(operator_client, traced_link):
    response = operator_client.post(f"/api/v1/ops/links/{traced_link.pk}/publish")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "recipe_incomplete"
    assert PublishedRecord.objects.count() == 0


def test_publish_with_unconnected_required_field_is_409(operator_client, traced_link):
    operator_client.post(f"/api/v1/ops/links/{traced_link.pk}/extractions")
    tables = operator_client.get(f"/api/v1/ops/links/{traced_link.pk}/tables").json()[
        "tables"
    ]
    column = dict(tables[0]["columns"][0])
    # Only one required field connected: the recipe stays incomplete.
    operator_client.put(
        f"/api/v1/ops/links/{traced_link.pk}/recipe",
        {
            "plan_type": "hosting",
            "bindings": [
                {
                    "schema_field_key": "plan_name",
                    "source_table_id": tables[0]["id"],
                    "source_column_id": column["id"],
                    "formula": "",
                }
            ],
        },
        format="json",
    )
    response = operator_client.post(f"/api/v1/ops/links/{traced_link.pk}/publish")
    assert response.status_code == 409
    assert PublishedRecord.objects.count() == 0


def test_catalog_never_imports_admin_console():
    import ast
    import pathlib

    catalog_root = pathlib.Path("backend/src/catalog")
    for path in catalog_root.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                assert not name.startswith("admin_console"), (
                    f"catalog imports admin_console in {path}"
                )
