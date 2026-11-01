"""US3 — deterministic page summary + recall-biased LLM refilter (FR-012..FR-015)."""

import pytest

from admin_console import services
from admin_console.models import Link
from admin_console.refilter import PageSummarizer

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


def test_summary_takes_headings_and_largest_main_or_article_block():
    html = (
        "<html><body>"
        "<main><p>tiny</p></main>"
        "<article><h1>Hosting plans</h1><h2>Pricing</h2>"
        "<p>" + ("cheap shared hosting plan " * 50) + "</p></article>"
        "<footer>ignore me</footer>"
        "</body></html>"
    )

    summary = PageSummarizer().summarize(html, "https://example.com/hosting")

    assert summary["url"] == "https://example.com/hosting"
    assert summary["headings"] == ["Hosting plans", "Pricing"]
    assert summary["important_section"].startswith("Hosting plans")
    assert "ignore me" not in summary["important_section"]


def test_model_receives_only_the_summary_never_html(
    candidate_link, stub_llm, stub_page_html
):
    stub_page_html.html = (
        '<main><script>RAW_HTML_ONLY_MARKER</script>'
        '<h1 data-secret="RAW_HTML_ATTR">Plans</h1><p>Cheap hosting</p></main>'
    )

    services.refilter_link(candidate_link)

    assert stub_page_html.fetched == [candidate_link.url]
    call = stub_llm.refilter_calls[0]
    assert set(call) == {"url", "headings", "important_section"}
    assert call["headings"] == ["Plans"]
    assert "<main>" not in str(call["important_section"])
    # Raw markup and script bodies never reach the model, only visible text does.
    assert "RAW_HTML_ONLY_MARKER" not in str(call["important_section"])
    assert "RAW_HTML_ATTR" not in str(call)
    assert "Cheap hosting" in str(call["important_section"])


def test_confidently_non_plans_link_is_dropped(candidate_link, stub_llm, stub_page_html):
    stub_llm.refilter_response = {
        "is_plans_page": False,
        "plan_type": "",
        "confidence": 0.95,
    }

    services.refilter_link(candidate_link)

    candidate_link.refresh_from_db()
    assert candidate_link.review_state == Link.ReviewState.DROPPED
    assert candidate_link.pipeline_stage == Link.PipelineStage.DISCOVERED


def test_borderline_link_is_kept_and_flagged(candidate_link, stub_llm, stub_page_html):
    stub_llm.refilter_response = {
        "is_plans_page": False,
        "plan_type": "",
        "confidence": 0.4,
    }

    services.refilter_link(candidate_link)

    candidate_link.refresh_from_db()
    assert candidate_link.review_state == Link.ReviewState.KEPT
    assert candidate_link.refilter_flag is True
    assert candidate_link.pipeline_stage == Link.PipelineStage.REFILTERED


def test_confident_plans_link_keeps_plan_type(candidate_link, stub_llm, stub_page_html):
    stub_llm.refilter_response = {
        "is_plans_page": True,
        "plan_type": "hosting",
        "confidence": 0.9,
    }

    services.refilter_link(candidate_link)

    candidate_link.refresh_from_db()
    assert candidate_link.review_state == Link.ReviewState.KEPT
    assert candidate_link.refilter_plan_type == "hosting"
    assert candidate_link.refilter_flag is False


def test_batch_refilter_sends_all_page_summaries_in_one_call(
    candidate_link, site, stub_llm, stub_page_html
):
    second = Link.objects.create(
        site=site,
        url="https://example.com/about",
        url_hash="second-candidate-hash",
        review_state=Link.ReviewState.CANDIDATE,
        pipeline_stage=Link.PipelineStage.DISCOVERED,
    )
    stub_llm.refilter_response = lambda url, headings, text: {
        "is_plans_page": url.endswith("hosting"),
        "plan_type": "hosting" if url.endswith("hosting") else "",
        "confidence": 0.99,
    }

    services.refilter_links([candidate_link, second])

    assert len(stub_llm.batch_refilter_calls) == 1
    pages = stub_llm.batch_refilter_calls[0]
    assert [page["index"] for page in pages] == [0, 1]
    assert all(set(page) == {"index", "url", "headings", "important_section"} for page in pages)
    candidate_link.refresh_from_db()
    second.refresh_from_db()
    assert candidate_link.review_state == Link.ReviewState.KEPT
    assert second.review_state == Link.ReviewState.DROPPED
    assert second.pipeline_task_state == "completed"
