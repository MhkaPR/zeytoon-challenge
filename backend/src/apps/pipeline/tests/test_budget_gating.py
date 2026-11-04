"""Cross-cutting — admin-owned LLM token budget gates every LLM stage (FR-047..FR-050)."""

import pytest

from apps.admin_console import llm, services
from apps.pipeline.models import Link, LlmCostLedger
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db


def _exhaust_budget():
    services.set_token_budget(100)
    llm.default_budget.record_spend("seed", 100, idempotency_key="seed-spend")


def test_budget_status_reports_budget_and_spend():
    services.set_token_budget(500)

    status = services.token_budget_status()

    assert status["token_budget"] == 500
    assert status["tokens_used"] == 0


def test_every_llm_stage_is_gated_and_parks_the_link(extracted_link, stub_domtrack):
    _exhaust_budget()
    assert llm.default_budget.allows() is False

    with pytest.raises(llm.LlmBudgetExhausted):
        services.label_link_tables(extracted_link)

    extracted_link.refresh_from_db()
    assert extracted_link.pipeline_stage == Link.PipelineStage.AWAITING_LLM_BUDGET
    assert extracted_link.last_error == "awaiting_llm_budget:labeling"
    assert Notification.objects.filter(event_type="llm_budget_exhausted").exists()


def test_no_partial_row_is_written_when_the_budget_is_exhausted(labeled_link):
    _exhaust_budget()

    with pytest.raises(llm.LlmBudgetExhausted):
        services.classify_and_extract_link_tables(labeled_link)

    from apps.pipeline.models import TableClassification

    assert TableClassification.objects.count() == 0


def test_non_llm_stages_continue_while_the_budget_is_exhausted(
    traced_link, stub_domtrack
):
    _exhaust_budget()

    services.extract_link_tables(traced_link)

    assert traced_link.extracted_tables.exists()


def _fake_chat_response(payload):
    import json

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": json.dumps(payload)}}],
                "usage": {"total_tokens": 7},
            }

    return _Response()


def test_a_restored_budget_resumes_the_stage(labeled_link, monkeypatch, settings):
    settings.OPENAI_BASE_URL = "http://llm.local"
    settings.OPENAI_API_KEY = "test-key"
    _exhaust_budget()
    with pytest.raises(llm.LlmBudgetExhausted):
        services.classify_and_extract_link_tables(labeled_link)

    # Restore the budget and let the real client run against a stubbed transport.
    monkeypatch.setattr(
        llm.httpx,
        "post",
        lambda *args, **kwargs: _fake_chat_response(
            {"tables": [{"table_index": 0, "is_correct": False}]}
        ),
    )
    services.set_token_budget(10_000)
    services.classify_and_extract_link_tables(labeled_link)

    labeled_link.refresh_from_db()
    assert labeled_link.pipeline_stage == Link.PipelineStage.NO_PLANS


def test_budget_can_be_set_by_an_admin_through_the_api(operator_client):
    response = operator_client.put(
        "/api/v1/ops/llm-token-budget", {"token_budget": 1234}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["token_budget"] == 1234
    assert LlmCostLedger.objects.filter(token_budget=1234).exists()


def test_one_batch_spend_row_is_associated_with_every_link(kept_link):
    second = Link.objects.create(
        site=kept_link.site,
        url="https://example.com/second",
        url_hash="second-cost-link",
    )

    row, created = llm.default_budget.record_spend(
        "labeling", 321, links=[kept_link, second], idempotency_key="batch-cost"
    )

    assert created is True
    assert row.tokens_used == 321
    assert row.link_ref is None
    assert set(row.links.values_list("pk", flat=True)) == {kept_link.pk, second.pk}
    assert LlmCostLedger.objects.filter(idempotency_key="batch-cost").count() == 1
