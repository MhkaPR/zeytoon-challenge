"""US7 — plan data extraction against the schema, data only (FR-026..FR-031)."""

import json

import pytest

from admin_console import plan_schema, services
from admin_console.models import (
    ExtractedTable,
    ExtractedTableColumn,
    ExtractedTableRow,
    Link,
    PlanRecord,
    TableClassification,
)
from admin_console.tests.conftest import HOSTING_PLAN_VALUES

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
            table=table, column_id=f"c{i}", label=label, path=f"td.c{i}",
            atype="text", coverage=1.0, row_count=2,
        )
    for r in range(2):
        ExtractedTableRow.objects.create(
            table=table, row_index=r,
            cells={f"c{i}": f"value {r}{i}" for i in range(len(labels))},
        )
    TableClassification.objects.create(
        table=table, is_plans_table=is_plans, plan_type=plan_type if is_plans else "",
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


def test_extraction_output_contains_no_selector_or_formula(planned_link, stub_llm):
    # The payload the model was asked to fill must be values only: no selectors or
    # formulas ever leave this stage (FR-028, SC-012).
    blob = json.dumps(PlanRecord.objects.get(link=planned_link).values)
    assert ">" not in blob
    assert "=" not in blob
    assert "${" not in blob
    assert "{{" not in blob


def test_unmappable_table_is_skipped_without_dropping_siblings(extracted_link, stub_llm):
    mappable = _add_classified_table(extracted_link, 1, ["Plan", "Price"])
    _add_classified_table(extracted_link, 2, ["Unmappable"], plan_type="hosting")

    def plans_for(table_context, plan_type):
        if "Unmappable" in table_context["columns"]:
            return []
        return [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 0.8}]

    stub_llm.plans = plans_for

    services.extract_link_plans(extracted_link)

    assert PlanRecord.objects.filter(table=mappable).count() == 1
    assert PlanRecord.objects.count() == 1


def test_re_extraction_is_idempotent(planned_link, stub_llm):
    stub_llm.plans = [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 0.8}]
    first = list(PlanRecord.objects.filter(link=planned_link).values_list("natural_key", flat=True))

    services.extract_link_plans(planned_link)

    assert list(
        PlanRecord.objects.filter(link=planned_link).values_list("natural_key", flat=True)
    ) == first


def test_no_plans_table_means_nothing_to_extract(extracted_link, stub_llm):
    stub_llm.classifications = [
        {"table_index": 0, "is_plans_table": False, "plan_type": "", "confidence": 0.9}
    ]
    services.classify_link_tables(extracted_link)

    with pytest.raises(ValueError, match="plans_required"):
        services.extract_link_plans(extracted_link)
