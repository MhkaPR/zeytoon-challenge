"""Cross-cutting — admin-owned LLM token budget gates every LLM stage (FR-047..FR-050)."""

import pytest

from admin_console import llm, services
from admin_console.models import Link, LlmCostLedger
from notifications.models import Notification

pytestmark = pytest.mark.django_db


def _exhaust_budget():
    services.set_token_budget(100)
    llm.default_budget.record_spend("seed", 100, idempotency_key="seed-spend")


def test_budget_status_reports_budget_and_spend():
    services.set_token_budget(500)

    status = services.token_budget_status()

    assert status["token_budget"] == 500
    assert status["tokens_used"] == 0


def test_every_llm_stage_is_gated_and_parks_the_link(kept_link):
    _exhaust_budget()
    assert llm.default_budget.allows() is False

    with pytest.raises(llm.LlmBudgetExhausted):
        services.refilter_link(kept_link, html="<main><h1>Plans</h1></main>")

    kept_link.refresh_from_db()
    assert kept_link.pipeline_stage == Link.PipelineStage.AWAITING_LLM_BUDGET
    assert kept_link.last_error == "awaiting_llm_budget:refilter"
    assert Notification.objects.filter(event_type="llm_budget_exhausted").exists()


def test_no_partial_row_is_written_when_the_budget_is_exhausted(extracted_link):
    _exhaust_budget()

    with pytest.raises(llm.LlmBudgetExhausted):
        services.classify_link_tables(extracted_link)

    from admin_console.models import TableClassification

    assert TableClassification.objects.count() == 0


def test_non_llm_stages_continue_while_the_budget_is_exhausted(traced_link, stub_domtrack):
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


def test_a_restored_budget_resumes_the_stage(kept_link, stub_page_html, monkeypatch,
                                             settings):
    settings.OPENAI_BASE_URL = "http://llm.local"
    settings.OPENAI_API_KEY = "test-key"
    _exhaust_budget()
    with pytest.raises(llm.LlmBudgetExhausted):
        services.refilter_link(kept_link)

    # Restore the budget and let the real client run against a stubbed transport.
    monkeypatch.setattr(
        llm.httpx, "post",
        lambda *args, **kwargs: _fake_chat_response(
            {"is_plans_page": True, "plan_type": "hosting", "confidence": 0.9}
        ),
    )
    services.set_token_budget(10_000)
    services.refilter_link(kept_link)

    kept_link.refresh_from_db()
    assert kept_link.review_state == Link.ReviewState.KEPT
    assert kept_link.pipeline_stage == Link.PipelineStage.REFILTERED


def test_budget_can_be_set_by_an_admin_through_the_api(operator_client):
    response = operator_client.put(
        "/api/v1/ops/llm-token-budget", {"token_budget": 1234}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["token_budget"] == 1234
    assert LlmCostLedger.objects.filter(token_budget=1234).exists()
