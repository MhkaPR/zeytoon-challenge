"""US6 — rule-based table classification (FR-023..FR-025)."""

import pytest

from apps.pipeline import llm
from apps.pipeline.models import ExtractedTable, Link, PlanRecord, TableClassification
from apps.pipeline.services.v1 import pipeline as services
from apps.pipeline.tests.conftest import HOSTING_PLAN_VALUES

pytestmark = pytest.mark.django_db


def test_price_table_is_detected_from_configured_rules(extracted_link):
    services.classify_tables_for_link(extracted_link)

    classification = TableClassification.objects.get(table__link=extracted_link)
    assert classification.is_price_table is True
    assert classification.matching_rows >= 2


def test_non_price_table_is_recorded_but_not_accepted(extracted_link):
    table = extracted_link.extracted_tables.get()
    table.rows.all().delete()
    table.rows.create(row_index=0, cells={"col-0": "About", "col-1": "us"})
    table.rows.create(row_index=1, cells={"col-0": "Contact", "col-1": "team"})

    services.classify_tables_for_link(extracted_link)

    classification = TableClassification.objects.get(table=table)
    assert classification.is_price_table is False


def test_each_table_is_classified_independently(extracted_link):
    first = extracted_link.extracted_tables.get()
    second = ExtractedTable.objects.create(
        trace=first.trace,
        link=extracted_link,
        table_index=1,
        parent="footer",
        score=0.2,
        column_count=2,
        row_count=2,
    )
    second.rows.create(row_index=0, cells={"col-0": "About", "col-1": "us"})
    second.rows.create(row_index=1, cells={"col-0": "Contact", "col-1": "team"})

    services.classify_tables_for_link(extracted_link)

    assert TableClassification.objects.get(table=first).is_price_table is True
    assert TableClassification.objects.get(table=second).is_price_table is False


def test_combined_step_extracts_plans_from_accepted_tables(planned_link):
    classification = TableClassification.objects.get(table__link=planned_link)
    assert classification.is_price_table is True
    assert classification.plan_type == "hosting"
    assert PlanRecord.objects.filter(link=planned_link).count() == 1
    assert planned_link.pipeline_stage == Link.PipelineStage.PLANS_EXTRACTED


def test_budget_exhaustion_parks_the_link(labeled_link, stub_llm):
    stub_llm.exhausted_stages = {"schema_extraction"}

    with pytest.raises(llm.LlmBudgetExhausted):
        services.classify_and_extract_link_tables(labeled_link)

    labeled_link.refresh_from_db()
    assert labeled_link.pipeline_stage == Link.PipelineStage.AWAITING_LLM_BUDGET
