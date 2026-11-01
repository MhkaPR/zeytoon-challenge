"""US6 — table classification with plan type + confidence (FR-023..FR-025)."""

import json

import pytest

from admin_console import llm, services
from admin_console.models import (
    ExtractedTable,
    ExtractedTableColumn,
    Link,
    PlanRecord,
    TableClassification,
)
from admin_console.tests.conftest import HOSTING_PLAN_VALUES

pytestmark = pytest.mark.django_db


def test_each_table_gets_one_verdict_with_confidence(planned_link):
    classification = TableClassification.objects.get(table__link=planned_link)
    assert classification.is_plans_table is True
    assert classification.plan_type == "hosting"
    assert 0.0 <= classification.confidence <= 1.0
    assert planned_link.pipeline_stage == Link.PipelineStage.PLANS_EXTRACTED


def test_a_page_may_hold_several_plans_tables(labeled_link, stub_llm):
    extracted_link = labeled_link
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
        {"table_index": 0, "is_correct": True, "plan_type": "hosting", "confidence": 0.9},
        {"table_index": 1, "is_correct": True, "plan_type": "cdn", "confidence": 0.7},
    ]
    stub_llm.plans = [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 1.0}]

    services.classify_and_extract_link_tables(extracted_link)

    assert TableClassification.objects.filter(
        table__link=extracted_link, is_plans_table=True
    ).count() == 2


def test_non_plans_table_is_recorded_but_not_counted(labeled_link, stub_llm):
    extracted_link = labeled_link
    stub_llm.classifications = [
        {"table_index": 0, "is_correct": False, "plan_type": "", "confidence": 0.95}
    ]
    stub_llm.plans = []

    services.classify_and_extract_link_tables(extracted_link)

    classification = TableClassification.objects.get(table__link=extracted_link)
    assert classification.is_plans_table is False


def test_no_accepted_table_marks_link_as_no_plans(labeled_link, stub_llm):
    extracted_link = labeled_link
    stub_llm.classifications = [
        {"table_index": 0, "is_correct": False, "plan_type": "", "confidence": 0.95}
    ]
    stub_llm.plans = []

    services.classify_and_extract_link_tables(extracted_link)

    extracted_link.refresh_from_db()
    assert extracted_link.pipeline_stage == Link.PipelineStage.NO_PLANS
    assert PlanRecord.objects.filter(link=extracted_link).count() == 0


def test_budget_exhaustion_parks_the_link(labeled_link, stub_llm):
    extracted_link = labeled_link
    stub_llm.exhausted_stages = {"classification"}

    with pytest.raises(llm.LlmBudgetExhausted):
        services.classify_and_extract_link_tables(extracted_link)

    extracted_link.refresh_from_db()
    assert extracted_link.pipeline_stage == Link.PipelineStage.AWAITING_LLM_BUDGET
    assert TableClassification.objects.filter(table__link=extracted_link).count() == 0


def test_combined_step_classifies_and_extracts_in_one_llm_call(labeled_link, stub_llm):
    extracted_link = labeled_link
    first = ExtractedTable.objects.get(link=extracted_link)
    second = ExtractedTable.objects.create(
        trace=first.trace,
        link=extracted_link,
        table_index=1,
        parent="footer",
        score=0.2,
        column_count=2,
        row_count=2,
    )
    stub_llm.classifications = [
        {"table_index": 0, "is_correct": True, "plan_type": "hosting", "confidence": 0.99},
        {"table_index": 1, "is_correct": False, "plan_type": "", "confidence": 0.0},
    ]
    stub_llm.plans = [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 1.0}]

    services.classify_and_extract_link_tables(extracted_link)

    assert len(stub_llm.combined_classification_calls) == 1
    assert stub_llm.plan_calls == []
    assert TableClassification.objects.get(table=second).is_plans_table is False
    assert PlanRecord.objects.filter(table=first).count() == 1
    assert extracted_link.pipeline_stage == Link.PipelineStage.PLANS_EXTRACTED


def test_combined_step_applies_nearest_persian_currency_scale(labeled_link, stub_llm):
    extracted_link = labeled_link
    table = ExtractedTable.objects.get(link=extracted_link)
    table.columns.all().delete()
    table.rows.all().delete()
    columns = ["plan", "unit_thousands", "unit_millions", "price"]
    for index, label in enumerate(columns):
        ExtractedTableColumn.objects.create(
            table=table,
            column_id=f"price-{index}",
            label=label,
            path=f"td.price-{index}",
        )
    table.rows.create(
        row_index=0,
        cells={
            "price-0": "Starter",
            "price-1": "هزار تومان",
            "price-2": "میلیون تومان",
            "price-3": "990",
        },
    )
    stub_llm.classifications = [
        {"table_index": 0, "is_correct": True, "plan_type": "hosting"}
    ]
    unscaled_values = dict(HOSTING_PLAN_VALUES, price_amount=990)
    stub_llm.plans = [{"values": unscaled_values, "confidence": 1.0}]

    services.classify_and_extract_link_tables(extracted_link)

    record = PlanRecord.objects.get(link=extracted_link)
    assert record.values["price_amount"] == 990_000_000


def test_combined_llm_response_uses_only_boolean_for_rejected_table(monkeypatch):
    client = llm.LlmClient()
    payload = {
        "tables": [
            {"table_index": 0, "is_correct": False},
            {
                "table_index": 1,
                "is_correct": True,
                "plan_type": "hosting",
                "confidence": 0.98,
                "plans": [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 1.0}],
            },
        ]
    }
    monkeypatch.setattr(client, "chat_json", lambda *args, **kwargs: payload)

    results = client.classify_extract_tables(
        [{"table_index": 0, "columns": [], "rows": []},
         {"table_index": 1, "columns": [], "rows": []}]
    )

    assert results[0].model_dump(exclude_none=True) == {
        "table_index": 0,
        "is_correct": False,
    }
    assert results[1].is_correct is True
    assert results[1].plans[0].values["plan_name"] == "Starter"


def test_combined_llm_response_rejects_extra_fields_for_incorrect_class(monkeypatch):
    client = llm.LlmClient()
    monkeypatch.setattr(
        client,
        "chat_json",
        lambda *args, **kwargs: {
            "tables": [{"table_index": 0, "is_correct": False, "plan_type": "hosting"}]
        },
    )

    with pytest.raises(llm.LlmError, match="only its Boolean verdict"):
        client.classify_extract_tables([{"table_index": 0, "columns": [], "rows": []}])


def test_combined_llm_response_accepts_classification_confidence_field(monkeypatch):
    client = llm.LlmClient()
    payload = {
        "tables": [{
            "table_index": 0,
            "is_correct": True,
            "plan_type": "hosting",
            "classification_confidence": 1.0,
            "plans": [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 1.0}],
        }]
    }
    monkeypatch.setattr(client, "chat_json", lambda *args, **kwargs: payload)

    results = client.classify_extract_tables(
        [{"table_index": 0, "columns": [], "rows": []}]
    )

    assert results[0].classification_confidence == 1.0


def test_combined_llm_response_moves_out_of_schema_fields_to_other(monkeypatch):
    client = llm.LlmClient()
    values = dict(HOSTING_PLAN_VALUES, location="Tehran", datacenter="DC1")
    payload = {
        "tables": [{
            "table_index": 0,
            "is_correct": True,
            "plan_type": "hosting",
            "classification_confidence": 0.97,
            "plans": [{"values": values, "confidence": 1.0}],
        }]
    }
    monkeypatch.setattr(client, "chat_json", lambda *args, **kwargs: payload)

    results = client.classify_extract_tables(
        [{"table_index": 0, "columns": [], "rows": []}]
    )

    verdict = results[0]
    assert verdict.is_correct is True
    kept = verdict.plans[0].values
    assert "location" not in kept and "datacenter" not in kept
    assert {"key": "location", "value": "Tehran"} in kept["other"]
    assert {"key": "datacenter", "value": "DC1"} in kept["other"]


def test_combined_pass_batches_large_table_pages(monkeypatch):
    client = llm.LlmClient()
    calls = []

    def fake_chat_json(system, user, **kwargs):
        contexts = json.loads(user)["tables"]
        calls.append(len(contexts))
        return {"tables": [
            {"table_index": context["table_index"], "is_correct": False}
            for context in contexts
        ]}

    monkeypatch.setattr(client, "chat_json", fake_chat_json)

    contexts = [
        {"table_index": index, "columns": [], "rows": []}
        for index in range(25)
    ]
    results = client.classify_extract_tables(contexts)

    assert len(calls) > 1
    assert all(size <= 10 for size in calls)
    assert [verdict.table_index for verdict in results] == list(range(25))


def test_combined_pass_tolerates_omitted_table_verdicts(monkeypatch):
    client = llm.LlmClient()
    payload = {
        "tables": [{
            "table_index": 0,
            "is_correct": True,
            "plan_type": "hosting",
            "classification_confidence": 0.9,
            "plans": [{"values": dict(HOSTING_PLAN_VALUES), "confidence": 1.0}],
        }]
    }
    monkeypatch.setattr(client, "chat_json", lambda *args, **kwargs: payload)

    results = client.classify_extract_tables([
        {"table_index": 0, "columns": [], "rows": []},
        {"table_index": 1, "columns": [], "rows": []},
    ])

    by_index = {verdict.table_index: verdict for verdict in results}
    assert by_index[0].is_correct is True
    assert by_index[1].is_correct is False
