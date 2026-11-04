"""US2 — adaptive discovery strategy + deterministic link policy (FR-008, FR-009)."""

import pathlib
import sys
import types
from types import SimpleNamespace

import pytest

from apps.pipeline.discovery import LinkDiscoverer

pytestmark = pytest.mark.django_db


def _install_fake_crawl4ai(monkeypatch):
    """Put a fake ``crawl4ai`` in ``sys.modules`` and capture the adaptive config."""
    captured = {}

    class FakeAdaptiveCrawler:
        def __init__(self, crawler, config):
            captured["config"] = config

        async def digest(self, start_url, query):
            captured["start_url"] = start_url
            captured["query"] = query
            return SimpleNamespace(crawled_urls=["https://example.com/plans"])

    class FakeAsyncWebCrawler:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

    fake_adaptive = types.ModuleType("crawl4ai.adaptive_crawler")
    fake_adaptive.AdaptiveConfig = lambda **kwargs: kwargs
    fake_adaptive.AdaptiveCrawler = FakeAdaptiveCrawler

    fake_crawl4ai = types.ModuleType("crawl4ai")
    fake_crawl4ai.AsyncWebCrawler = FakeAsyncWebCrawler

    monkeypatch.setitem(sys.modules, "crawl4ai", fake_crawl4ai)
    monkeypatch.setitem(sys.modules, "crawl4ai.adaptive_crawler", fake_adaptive)
    return captured


def test_adaptive_crawl_uses_statistical_strategy_no_llm(monkeypatch):
    captured = _install_fake_crawl4ai(monkeypatch)

    urls = LinkDiscoverer().crawl_candidate_links("example.com", "hosting plans")

    assert urls == ["https://example.com/plans"]
    assert captured["config"]["strategy"] == "statistical"
    assert captured["start_url"] == "https://example.com"
    assert captured["query"] == "hosting plans"


def test_discovery_never_consults_a_sitemap():
    source = (pathlib.Path(__file__).resolve().parents[5] / "backend/src/apps/pipeline/discovery.py").read_text().lower()
    assert "sitemap" not in source


def test_link_policy_denies_extensions_segments_and_offsite():
    discoverer = LinkDiscoverer()
    urls = [
        "https://example.com/plans",
        "https://example.com/bundle.js",
        "https://example.com/robots.txt",
        "https://example.com/logo.png",
        "https://example.com/blog/post",
        "https://example.com/pricing?ref=x#frag",
        "https://other.com/plans",
        "https://example.com/plans",
    ]

    result = discoverer.apply_link_policy(urls, host="example.com")

    assert result == ["https://example.com/plans", "https://example.com/pricing"]


def test_link_policy_caps_the_candidate_set():
    urls = [f"https://example.com/p{i}" for i in range(10)]
    result = LinkDiscoverer().apply_link_policy(urls, host="example.com", max_links=3)
    assert len(result) == 3
