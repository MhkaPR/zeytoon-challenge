"""US3 — refilter + operator override endpoints (FR-012..FR-015)."""

import pytest

from admin_console.models import Link

pytestmark = pytest.mark.django_db


@pytest.fixture
def candidate_link(site):
    return Link.objects.create(
        site=site,
        url="https://example.com/hosting",
        url_hash="candidate-hash",
        source=Link.Source.ADAPTIVE_CRAWL,
        review_state=Link.ReviewState.CANDIDATE,
        pipeline_stage=Link.PipelineStage.DISCOVERED,
    )


def test_refilter_endpoint_keeps_a_plans_page(operator_client, candidate_link,
                                              stub_llm, stub_page_html):
    response = operator_client.post(f"/api/v1/ops/links/{candidate_link.pk}/refilter")

    assert response.status_code == 200
    assert response.json()["link"]["review_state"] == Link.ReviewState.KEPT


def test_refilter_endpoint_returns_202_when_budget_is_exhausted(
    operator_client, candidate_link, stub_llm, stub_page_html
):
    stub_llm.exhausted_stages = {"refilter"}

    response = operator_client.post(f"/api/v1/ops/links/{candidate_link.pk}/refilter")

    assert response.status_code == 202
    assert response.json()["error"]["code"] == "awaiting_llm_budget"


def test_operator_can_override_a_verdict(operator_client, candidate_link,
                                         stub_llm, stub_page_html):
    response = operator_client.post(
        f"/api/v1/ops/links/{candidate_link.pk}/refilter/override",
        {"refilter_state": "dropped", "reason": "not a plans page"},
        format="json",
    )

    assert response.status_code == 200
    candidate_link.refresh_from_db()
    assert candidate_link.review_state == Link.ReviewState.DROPPED
