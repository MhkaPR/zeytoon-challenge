"""Sitemap discovery unit tests (US2, FR-008, Principle X)."""

import pytest

from admin_console import discovery

pytestmark = pytest.mark.django_db


class _FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


class _FakeFetcher:
    """Fetcher double: robots.txt, sitemap and index bodies keyed by URL."""

    def __init__(self, bodies, robots_sitemaps=(), delay=0):
        self.bodies = bodies
        self._sitemaps = list(robots_sitemaps)
        self.delay = delay

    def robots_for(self, scheme, host):
        return self

    def allowed(self, url):
        return True

    def site_maps(self):
        return self._sitemaps

    def get(self, url):
        return _FakeResponse(
            self.bodies.get(url, ""), 200 if url in self.bodies else 404
        )


_URLSET = """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{base}/a</loc></url>
  <url><loc>{base}/b</loc></url>
</urlset>"""

_INDEX = """<?xml version="1.0"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>{base}/nested.xml</loc></sitemap>
</sitemapindex>"""


def test_robots_sitemap_directive_is_honored():
    fetcher = _FakeFetcher(
        {"https://example.com/custom.xml": _URLSET.format(base="https://example.com")},
        robots_sitemaps=["https://example.com/custom.xml"],
    )
    base, candidates = discovery.discover_sitemaps("example.com", fetcher=fetcher)
    assert base == "https://example.com"
    assert candidates[0] == "https://example.com/custom.xml"


def test_sitemap_xml_is_the_fallback():
    fetcher = _FakeFetcher({})
    _, candidates = discovery.discover_sitemaps("example.com", fetcher=fetcher)
    assert candidates == ["https://example.com/sitemap.xml"]


def test_index_is_followed_and_links_normalized():
    fetcher = _FakeFetcher(
        {
            "https://example.com/sitemap.xml": _INDEX.format(base="https://example.com"),
            "https://example.com/nested.xml": _URLSET.format(base="https://example.com"),
        }
    )
    links = discovery.discover_links("https://example.com/sitemap.xml", fetcher=fetcher)
    assert "https://example.com/a" in links
    assert "https://example.com/b" in links


def test_index_depth_is_bounded(monkeypatch):
    monkeypatch.setattr(discovery.constants, "sitemap_max_index_depth", lambda: 0)
    fetcher = _FakeFetcher(
        {
            "https://example.com/sitemap.xml": _INDEX.format(base="https://example.com"),
            "https://example.com/nested.xml": _URLSET.format(base="https://example.com"),
        }
    )
    links = discovery.discover_links("https://example.com/sitemap.xml", fetcher=fetcher)
    assert links == []


def test_relative_locs_are_made_absolute():
    body = (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<url><loc>/rel</loc></url></urlset>"
    )
    fetcher = _FakeFetcher({"https://example.com/sitemap.xml": body})
    links = discovery.discover_links("https://example.com/sitemap.xml", fetcher=fetcher)
    assert links == ["https://example.com/rel"]


def test_transparent_user_agent_is_configured():
    from django.conf import settings

    assert "TorobPlanBot" in settings.CRAWLER_USER_AGENT
    assert "contact:" in settings.CRAWLER_USER_AGENT
