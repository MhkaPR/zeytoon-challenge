"""Sitemap discovery honoring robots.txt (FR-008, research R5, Principle X).

Uses only stdlib :mod:`xml.etree.ElementTree` plus :mod:`httpx` for fetching. Requests
send the transparent project user-agent with a contact URL and honor the site's crawl
delay.
"""

import gzip
import logging
import time
import urllib.parse
import urllib.robotparser
import xml.etree.ElementTree as ET

import httpx
from django.conf import settings

from admin_console import constants

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
logger = logging.getLogger(__name__)


class _Fetcher:
    """Small HTTP fetcher honoring robots.txt and a per-domain delay."""

    def __init__(self, timeout):
        self.timeout = timeout
        self._last_request = {}
        self._robots = {}
        self.headers = {"User-Agent": settings.CRAWLER_USER_AGENT}

    def _delay(self, host):
        delay = settings.CRAWLER_REQUEST_DELAY_SECONDS
        last = self._last_request.get(host)
        if last is not None:
            elapsed = time.monotonic() - last
            if elapsed < delay:
                time.sleep(delay - elapsed)
        self._last_request[host] = time.monotonic()

    def robots_for(self, scheme, host):
        key = f"{scheme}://{host}"
        if key in self._robots:
            return self._robots[key]
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(f"{key}/robots.txt")
        try:
            response = httpx.get(
                f"{key}/robots.txt",
                headers=self.headers,
                timeout=self.timeout,
                follow_redirects=True,
            )
            if response.status_code == 200:
                parser.parse(response.text.splitlines())
            else:
                parser.parse([])
        except httpx.HTTPError:
            parser.parse([])
        self._robots[key] = parser
        return parser

    def allowed(self, url):
        parts = urllib.parse.urlsplit(url)
        parser = self.robots_for(parts.scheme, parts.netloc)
        try:
            return parser.can_fetch(settings.CRAWLER_USER_AGENT, url)
        except Exception:
            return True

    def get(self, url):
        parts = urllib.parse.urlsplit(url)
        self._delay(parts.netloc)
        return httpx.get(
            url, headers=self.headers, timeout=self.timeout, follow_redirects=True
        )


def _normalize(base_url, loc):
    return urllib.parse.urljoin(base_url, (loc or "").strip())


def _local_name(tag):
    return str(tag).rsplit("}", 1)[-1]


def _child_text(node, name):
    for child in node:
        if _local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _parse_sitemap(text, base_url):
    """Return ``(child_sitemaps, page_locs)`` from a sitemap body.

    Real-world sitemaps are inconsistent about the XML namespace: the spec encourages
    ``xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"``, but many generators (and
    hand-written files) omit it. Matching on the local tag name handles both.
    """
    child_sitemaps, page_locs = [], []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return child_sitemaps, page_locs
    tag = _local_name(root.tag)
    if tag == "sitemapindex":
        for sitemap in root:
            if _local_name(sitemap.tag) != "sitemap":
                continue
            loc = _child_text(sitemap, "loc")
            if loc:
                child_sitemaps.append(_normalize(base_url, loc))
    elif tag == "urlset":
        for url in root:
            if _local_name(url.tag) != "url":
                continue
            loc = _child_text(url, "loc")
            if loc:
                page_locs.append(_normalize(base_url, loc))
    return child_sitemaps, page_locs


def _response_text(response):
    """Decode a sitemap body, transparently handling an unlabelled gzip file."""
    body = getattr(response, "content", b"") or b""
    if not body:
        return response.text
    if body[:2] == b"\x1f\x8b":
        try:
            body = gzip.decompress(body)
        except OSError:
            pass
    return body.decode(getattr(response, "encoding", None) or "utf-8", errors="replace")


def discover_sitemaps(domain, fetcher=None):
    """Find the site's sitemap URL(s): robots.txt directives, then /sitemap.xml."""
    fetcher = fetcher or _Fetcher(constants.sitemap_fetch_timeout_seconds())
    if "://" not in domain:
        domain = f"https://{domain}"
    parts = urllib.parse.urlsplit(domain)
    base = f"{parts.scheme}://{parts.netloc}"

    candidates = []
    parser = fetcher.robots_for(parts.scheme, parts.netloc)
    for line in getattr(parser, "site_maps", lambda: [])() or []:
        candidates.append(_normalize(base, line))
    # Always keep the conventional URL as a fallback: a stale robots.txt directive must
    # not hide a perfectly good /sitemap.xml.
    fallback = f"{base}/sitemap.xml"
    if fallback not in candidates:
        candidates.append(fallback)
    return base, candidates


def discover_links(sitemap_url, fetcher=None, _depth=0):
    """Enumerate page links from a sitemap, following nested sitemap indexes."""
    fetcher = fetcher or _Fetcher(constants.sitemap_fetch_timeout_seconds())
    max_depth = constants.sitemap_max_index_depth()
    links = []
    try:
        response = fetcher.get(sitemap_url)
    except httpx.HTTPError as exc:
        logger.warning("sitemap.fetch_failed url=%s error=%s", sitemap_url, exc)
        return links
    if response.status_code != 200:
        logger.warning(
            "sitemap.unexpected_status url=%s status=%s", sitemap_url, response.status_code
        )
        return links
    children, page_locs = _parse_sitemap(_response_text(response), sitemap_url)
    if not children and not page_locs:
        logger.warning("sitemap.unparsed url=%s", sitemap_url)
    links.extend(page_locs)
    if _depth < max_depth:
        for child in children:
            links.extend(discover_links(child, fetcher=fetcher, _depth=_depth + 1))
    return links


def discover_site_links(domain, fetcher=None):
    """Return ``(sitemap_url, links)`` for a domain; ``sitemap_url`` empty when none."""
    fetcher = fetcher or _Fetcher(constants.sitemap_fetch_timeout_seconds())
    _, candidates = discover_sitemaps(domain, fetcher=fetcher)
    for candidate in candidates:
        links = discover_links(candidate, fetcher=fetcher)
        if links:
            # De-duplicate while preserving order.
            seen, unique = set(), []
            for link in links:
                if link not in seen:
                    seen.add(link)
                    unique.append(link)
            return candidate, unique
    return "", []
