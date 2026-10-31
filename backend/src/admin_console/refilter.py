"""Deterministic page summary + the LLM link refilter (FR-012..FR-014).

``PageSummarizer`` derives the URL, its ``h1``-``h3`` headings, and the important section
(the largest text-density block inside ``<main>``/``<article>``) **without an LLM**; only
that summary is sent to the model, never the page HTML (SC-007).

``LinkRefilter`` glues the fetch, the summary, and the LLM verdict together. Both are
small classes you can subclass or inject fakes into for tests.
"""

import urllib.parse
from html.parser import HTMLParser

import httpx
from django.conf import settings

from admin_console import constants, llm

_STRIP_TAGS = {
    "script", "style", "noscript", "template", "svg", "nav", "footer", "header", "form",
}
_BLOCK_TAGS = {"main", "article"}
IMPORTANT_SECTION_MAX_CHARS = 4000


class PageSummarizer:
    """Deterministic extraction of the refilter input from normal HTML (FR-012)."""

    def summarize(self, html, url):
        parser = _SummaryParser()
        parser.feed(html or "")
        headings = parser.headings["h1"] + parser.headings["h2"] + parser.headings["h3"]
        return {
            "url": url,
            "headings": headings,
            "important_section": parser.important_section(),
        }

    def fetch_html(self, url, timeout=None):
        """Fetch a page's normal HTML with the transparent crawler user-agent."""
        response = httpx.get(
            url,
            headers={"User-Agent": settings.CRAWLER_USER_AGENT},
            timeout=timeout or 20.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        return response.text


class _SummaryParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.headings = {"h1": [], "h2": [], "h3": []}
        self._heading_stack = []
        self._strip_depth = 0
        self._blocks = []
        self._block_stack = []
        self._current = None
        self._text_buffer = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _STRIP_TAGS:
            self._strip_depth += 1
            return
        if tag in ("h1", "h2", "h3"):
            self._heading_stack.append(tag)
            self._text_buffer = []
        if tag in _BLOCK_TAGS:
            self._block_stack.append(tag)
            self._current = []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _STRIP_TAGS:
            if self._strip_depth:
                self._strip_depth -= 1
            return
        if tag in ("h1", "h2", "h3") and self._heading_stack:
            self._heading_stack.pop()
            text = " ".join("".join(self._text_buffer).split())
            if text:
                self.headings[tag].append(text)
            self._text_buffer = []
        if tag in _BLOCK_TAGS and self._block_stack:
            self._block_stack.pop()
            text = " ".join("".join(self._current or []).split())
            if text:
                self._blocks.append(text)
            self._current = [] if self._block_stack else None

    def handle_data(self, data):
        if self._strip_depth:
            return
        if self._heading_stack:
            self._text_buffer.append(data)
        if self._current is not None:
            self._current.append(data)

    def important_section(self):
        if not self._blocks:
            return ""
        return max(self._blocks, key=len)[:IMPORTANT_SECTION_MAX_CHARS]


class LinkRefilter:
    """Fetch → summarize → LLM verdict, with the recall-biased drop rule (FR-013)."""

    def __init__(self, llm_client=None, summarizer=None):
        self.llm = llm_client or llm.default_client
        self.summarizer = summarizer or PageSummarizer()

    def refilter(self, url, html=None, *, link=None, idempotency_key=None):
        page_html = html if html is not None else self.summarizer.fetch_html(url)
        summary = self.summarizer.summarize(page_html, url)
        return self.llm.refilter_page(
            summary["url"],
            summary["headings"],
            summary["important_section"],
            link=link,
            idempotency_key=idempotency_key,
        )

    @staticmethod
    def should_drop(verdict):
        """Drop only a confidently non-plans verdict; keep borderline (FR-014)."""
        return (
            not verdict.is_plans_page
            and verdict.confidence >= constants.refilter_drop_confidence()
        )


default_refilter = LinkRefilter()
default_summarizer = PageSummarizer()


def summarize_page(html, url):
    return default_summarizer.summarize(html, url)


def fetch_html(url, timeout=None):
    return default_summarizer.fetch_html(url, timeout)


def refilter_page(url, html, *, idempotency_key=None, link=None):
    return default_refilter.refilter(url, html, link=link, idempotency_key=idempotency_key)


def should_drop(verdict):
    return LinkRefilter.should_drop(verdict)
