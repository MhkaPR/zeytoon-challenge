"""US7 — plan data extraction against the schema, data only (FR-026..FR-031)."""

import json

import pytest

from apps.admin_console import llm, plan_schema, services
from apps.admin_console.models import (
    ExtractedTable,
    ExtractedTableColumn,
    ExtractedTableRow,
    Link,
    PlanRecord,
    TableClassification,
)
from apps.admin_console.tests.conftest import HOSTING_PLAN_VALUES

pytestmark = pytest.mark.django_db


def _add_classified_table(link, index, labels, is_plans=True, plan_type="hosting"):
    table = ExtractedTable.objects.create(
        trace=link.current_trace,
        link=link,
        table_index=index,
        parent=f"div#{index}",
        score=0.5,
        column_count=len(labels),
        row_count=2,
    )
    for i, label in enumerate(labels):
        ExtractedTableColumn.objects.create(
            table=table,
            column_id=f"c{i}",
            label=label,
            path=f"td.c{i}",
            atype="text",
            coverage=1.0,
            row_count=2,
        )
    for r in range(2):
        ExtractedTableRow.objects.create(
            table=table,
            row_index=r,
            cells={f"c{i}": f"value {r}{i}" for i in range(len(labels))},
        )
    TableClassification.objects.create(
        table=table,
        is_plans_table=is_plans,
        plan_type=plan_type if is_plans else "",
        confidence=0.9,
    )
    return table


def test_plan_records_are_normalized_schema_data(planned_link):
    plan = PlanRecord.objects.get(link=planned_link)
    assert plan.plan_type == "hosting"
    assert set(plan.values) <= plan_schema.all_field_keys("hosting")
    assert plan.values["plan_name"] == "Starter"
    assert plan.values["price_amount"] == 50000
    assert plan.values["billing_period"] == "monthly"
    assert planned_link.pipeline_stage == Link.PipelineStage.PLANS_EXTRACTED


def test_llm_plan_parser_skips_malformed_items_and_keeps_valid_plans(monkeypatch):
    client = llm.LlmClient()
    monkeypatch.setattr(
        client,
        "chat_json",
        lambda *args, **kwargs: {
            "plans": [
                {"confidence": 0.9},
                {"values": dict(HOSTING_PLAN_VALUES), "confidence": 0.8},
            ]
        },
    )

    plans = client.extract_plans({}, "hosting", plan_schema.all_field_keys("hosting"))

    assert len(plans) == 1
    assert plans[0].values["plan_name"] == "Starter"


def test_llm_plan_parser_rejects_response_with_no_valid_items(monkeypatch):
    client = llm.LlmClient()
    monkeypatch.setattr(
        client, "chat_json", lambda *args, **kwargs: {"plans": [{"confidence": 0.9}]}
    )

    with pytest.raises(llm.LlmError, match="no valid plan records"):
        client.extract_plans({}, "hosting", plan_schema.all_field_keys("hosting"))


def test_extraction_output_contains_no_selector_or_formula(planned_link, stub_llm):
    # The payload the model was asked to fill must be values only: no selectors or
    # formulas ever leave this stage (FR-028, SC-012).
    blob = json.dumps(PlanRecord.objects.get(link=planned_link).values)
    assert ">" not in blob
    assert "=" not in blob
    assert "${" not in blob
    assert "{{" not in blob


def test_unmappable_table_is_skipped_without_dropping_siblings(
    extracted_link, stub_llm
):
    mappable = _add_classified_table(extracted_link, 1, ["Plan", "Price"])
    _add_classified_table(extracted_link, 2, ["Unmappable"], plan_type="hosting")

    def plans_for(table_context, plan_type):
        if "Unmappable" in table_context["columns"]:
            return []
        return [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 1.0}]

    stub_llm.plans = plans_for

    services.extract_link_plans(extracted_link)

    assert PlanRecord.objects.filter(table=mappable).count() == 1
    assert PlanRecord.objects.count() == 1


def test_duplicate_plan_names_across_tables_get_unique_link_keys(
    extracted_link, stub_llm
):
    _add_classified_table(extracted_link, 1, ["Plan", "Price"])
    _add_classified_table(extracted_link, 2, ["Plan", "Price"])
    stub_llm.plans = [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 1.0}]

    services.extract_link_plans(extracted_link)

    records = list(PlanRecord.objects.filter(link=extracted_link))
    assert len(records) == 2
    assert len({record.natural_key for record in records}) == 2

    services.extract_link_plans(extracted_link)
    assert PlanRecord.objects.filter(link=extracted_link).count() == 2


def test_extraction_accepts_name_price_without_server_specs(extracted_link, stub_llm):
    _add_classified_table(extracted_link, 1, ["Plan", "Price"])
    stub_llm.plans = [
        {"values": {"plan_name": "Basic", "price_amount": 120000}, "confidence": 1.0}
    ]

    services.extract_link_plans(extracted_link)

    record = PlanRecord.objects.get(link=extracted_link)
    assert record.values == {"plan_name": "Basic", "price_amount": 120000}


@pytest.mark.parametrize("price", [0, None, ""])
def test_extraction_rejects_missing_or_zero_price(extracted_link, stub_llm, price):
    _add_classified_table(extracted_link, 1, ["Plan", "Price"])
    stub_llm.plans = [
        {"values": {"plan_name": "No price", "price_amount": price}, "confidence": 1.0}
    ]

    with pytest.raises(llm.LlmError, match="no plan records met confidence"):
        services.extract_link_plans(extracted_link)

    assert PlanRecord.objects.filter(link=extracted_link).count() == 0


def test_low_confidence_plans_pause_and_preserve_existing_records(
    planned_link, stub_llm
):
    original = PlanRecord.objects.get(link=planned_link)
    stub_llm.plans = [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 0.99}]

    with pytest.raises(llm.LlmError, match="no plan records met confidence"):
        services.extract_link_plans(planned_link)

    assert PlanRecord.objects.get(link=planned_link).pk == original.pk
    planned_link.refresh_from_db()
    assert planned_link.pipeline_stage == Link.PipelineStage.PLANS_EXTRACTED


def test_plan_exclusion_survives_reextraction(planned_link, stub_llm):
    record = PlanRecord.objects.get(link=planned_link)
    services.set_plan_excluded(planned_link, record, True)
    changed_price = dict(HOSTING_PLAN_VALUES, price_amount=87500)
    stub_llm.plans = [{"values": changed_price, "confidence": 1.0}]

    services.extract_link_plans(planned_link)

    assert services.plans_payload(planned_link)[0]["ignored"] is True
    assert services.unignored_plan_keys(planned_link) == set()


def test_re_extraction_is_idempotent(planned_link, stub_llm):
    stub_llm.plans = [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 1.0}]
    first = list(
        PlanRecord.objects.filter(link=planned_link).values_list(
            "natural_key", flat=True
        )
    )

    services.extract_link_plans(planned_link)

    assert (
        list(
            PlanRecord.objects.filter(link=planned_link).values_list(
                "natural_key", flat=True
            )
        )
        == first
    )


def test_no_plans_table_means_nothing_to_extract(extracted_link, stub_llm):
    table = ExtractedTable.objects.get(link=extracted_link)
    TableClassification.objects.create(
        table=table, is_plans_table=False, plan_type="", confidence=0.9
    )

    with pytest.raises(ValueError, match="plans_required"):
        services.extract_link_plans(extracted_link)
