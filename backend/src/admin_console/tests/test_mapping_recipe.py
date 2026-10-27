"""Mapping/recipe contract tests (US6, FR-025..FR-031, SC-009)."""

import pytest

from admin_console.models import ExtractionRecipe, Link, RecipeFieldBinding

pytestmark = pytest.mark.django_db


def _extract(operator_client, link):
    response = operator_client.post(f"/api/v1/ops/links/{link.pk}/extractions")
    assert response.status_code == 201
    tables = operator_client.get(f"/api/v1/ops/links/{link.pk}/tables").json()["tables"]
    return tables


def _binding_for(field_key, column, formula):
    return {
        "schema_field_key": field_key,
        "source_table_id": column["table_id"],
        "source_column_id": column["id"],
        "selector": column["path"],
        "formula": formula,
    }


def _first_column(tables):
    table = tables[0]
    column = dict(table["columns"][0])
    column["table_id"] = table["id"]
    return column


def test_plan_schema_endpoint_lists_plan_types(operator_client):
    response = operator_client.get("/api/v1/ops/plan-schema")
    assert response.status_code == 200
    keys = {plan["key"] for plan in response.json()["plan_types"]}
    assert {"hosting", "cdn", "virtual_server"} <= keys


def test_save_recipe_records_selector_and_formula(operator_client, traced_link):
    tables = _extract(operator_client, traced_link)
    column = _first_column(tables)
    bindings = [
        _binding_for(key, column, "=SUM(A2:A9)")
        for key in (
            "plan_name",
            "storage_amount",
            "storage_unit",
            "ram_amount",
            "cpu_cores",
            "bandwidth_amount",
            "price_amount",
            "billing_period",
        )
    ]
    response = operator_client.put(
        f"/api/v1/ops/links/{traced_link.pk}/recipe",
        {"plan_type": "hosting", "bindings": bindings},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recipe"]["is_complete"] is True
    assert body["link"]["pipeline_stage"] == Link.PipelineStage.MAPPED

    recipe = ExtractionRecipe.objects.get(link=traced_link, is_current=True)
    assert recipe.is_complete is True
    assert recipe.bindings.count() == len(bindings)
    binding = recipe.bindings.get(schema_field_key="plan_name")
    assert binding.selector == column["path"]
    assert binding.formula == "=SUM(A2:A9)"

    traced_link.refresh_from_db()
    assert traced_link.pipeline_stage == Link.PipelineStage.MAPPED


def test_incomplete_recipe_is_409_and_link_not_mapped(operator_client, traced_link):
    tables = _extract(operator_client, traced_link)
    column = _first_column(tables)
    # Only one of the eight required hosting fields is connected.
    bindings = [_binding_for("plan_name", column, "=A2")]
    response = operator_client.put(
        f"/api/v1/ops/links/{traced_link.pk}/recipe",
        {"plan_type": "hosting", "bindings": bindings},
        format="json",
    )
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "recipe_incomplete"
    assert "price_amount" in body["error"]["fields"]["unconnected"]

    traced_link.refresh_from_db()
    assert traced_link.pipeline_stage != Link.PipelineStage.MAPPED
    assert ExtractionRecipe.objects.get(link=traced_link, is_current=True).is_complete is False


def test_invalid_formula_and_unknown_field_are_400(operator_client, traced_link):
    tables = _extract(operator_client, traced_link)
    column = _first_column(tables)

    bad_formula = operator_client.put(
        f"/api/v1/ops/links/{traced_link.pk}/recipe",
        {
            "plan_type": "hosting",
            "bindings": [_binding_for("plan_name", column, "=NOPE(1)")],
        },
        format="json",
    )
    assert bad_formula.status_code == 400
    assert bad_formula.json()["error"]["code"] == "invalid_field"

    bad_field = operator_client.put(
        f"/api/v1/ops/links/{traced_link.pk}/recipe",
        {
            "plan_type": "hosting",
            "bindings": [_binding_for("not_a_field", column, "=A2")],
        },
        format="json",
    )
    assert bad_field.status_code == 400
    assert bad_field.json()["error"]["code"] == "invalid_field"

    bad_column = operator_client.put(
        f"/api/v1/ops/links/{traced_link.pk}/recipe",
        {
            "plan_type": "hosting",
            "bindings": [
                {
                    "schema_field_key": "plan_name",
                    "source_column_id": 999999,
                    "formula": "=A2",
                }
            ],
        },
        format="json",
    )
    assert bad_column.status_code == 400
    assert bad_column.json()["error"]["code"] == "invalid_field"


def test_get_recipe_restores_saved_bindings(operator_client, traced_link):
    tables = _extract(operator_client, traced_link)
    column = _first_column(tables)
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
    bindings = [_binding_for(key, column, "=A2") for key in required]
    operator_client.put(
        f"/api/v1/ops/links/{traced_link.pk}/recipe",
        {"plan_type": "hosting", "bindings": bindings},
        format="json",
    )

    response = operator_client.get(f"/api/v1/ops/links/{traced_link.pk}/recipe")
    assert response.status_code == 200
    recipe = response.json()["recipe"]
    assert recipe["plan_type"] == "hosting"
    restored = {b["schema_field_key"]: b for b in recipe["bindings"]}
    assert set(restored) == set(required)
    assert restored["plan_name"]["selector"] == column["path"]
    assert restored["plan_name"]["formula"] == "=A2"
    assert RecipeFieldBinding.objects.filter(recipe__link=traced_link).count() == len(
        required
    )
