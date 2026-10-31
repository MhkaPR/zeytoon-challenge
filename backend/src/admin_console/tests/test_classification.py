"""US6 — table classification with plan type + confidence (FR-023..FR-025)."""

import pytest

from admin_console import llm, services
from admin_console.models import ExtractedTable, Link, TableClassification

pytestmark = pytest.mark.django_db


def test_each_table_gets_one_verdict_with_confidence(classified_link):
    classification = TableClassification.objects.get(table__link=classified_link)
    assert classification.is_plans_table is True
    assert classification.plan_type == "hosting"
    assert 0.0 <= classification.confidence <= 1.0
    assert classified_link.pipeline_stage == Link.PipelineStage.CLASSIFIED


def test_a_page_may_hold_several_plans_tables(extracted_link, stub_llm):
    first = ExtractedTable.objects.get(link=extracted_link)
    ExtractedTable.objects.create(
        trace=first.trace,
        link=extracted_link,
        table_index=1,
        parent="div",
        score=0.5,
        column_count=2,
        row_count=2,
    )
    stub_llm.classifications = [
        {"table_index": 0, "is_plans_table": True, "plan_type": "hosting", "confidence": 0.9},
        {"table_index": 1, "is_plans_table": True, "plan_type": "cdn", "confidence": 0.7},
    ]

    services.classify_link_tables(extracted_link)

    assert TableClassification.objects.filter(
        table__link=extracted_link, is_plans_table=True
    ).count() == 2


def test_non_plans_table_is_recorded_but_not_counted(extracted_link, stub_llm):
    stub_llm.classifications = [
        {"table_index": 0, "is_plans_table": False, "plan_type": "", "confidence": 0.95}
    ]

    services.classify_link_tables(extracted_link)

    classification = TableClassification.objects.get(table__link=extracted_link)
    assert classification.is_plans_table is False


def test_budget_exhaustion_parks_the_link(extracted_link, stub_llm):
    stub_llm.exhausted_stages = {"classification"}

    with pytest.raises(llm.LlmBudgetExhausted):
        services.classify_link_tables(extracted_link)

    extracted_link.refresh_from_db()
    assert extracted_link.pipeline_stage == Link.PipelineStage.AWAITING_LLM_BUDGET
    assert TableClassification.objects.filter(table__link=extracted_link).count() == 0
