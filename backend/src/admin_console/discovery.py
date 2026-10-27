"""Sitemap discovery honoring robots.txt (FR-008, research R5, Principle X).

Uses only stdlib :mod:`xml.etree.ElementTree` plus :mod:`httpx` for fetching. Requests
send the transparent project user-agent with a contact URL and honor the site's crawl
delay.
"""

import time
import urllib.parse
import urllib.robotparser
import xml.etree.ElementTree as ET

import httpx
from django.conf import settings

from admin_console import constants

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


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


def _parse_sitemap(text, base_url):
    """Return ``(child_sitemaps, page_locs)`` parsed from a sitemap/robots body."""
    child_sitemaps, page_locs = [], []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return child_sitemaps, page_locs
    tag = root.tag.split("}")[-1]
    if tag == "sitemapindex":
        for sitemap in root.findall("sm:sitemap", _NS) or root.findall("sitemap"):
            loc = sitemap.findtext("sm:loc", namespaces=_NS)
            if loc:
                child_sitemaps.append(_normalize(base_url, loc))
    elif tag == "urlset":
        for url in root.findall("sm:url", _NS) or root.findall("url"):
            loc = url.findtext("sm:loc", namespaces=_NS)
            if loc:
                page_locs.append(_normalize(base_url, loc))
    return child_sitemaps, page_locs


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
    if not candidates:
        candidates.append(f"{base}/sitemap.xml")
    return base, candidates


def discover_links(sitemap_url, fetcher=None, _depth=0):
    """Enumerate page links from a sitemap, following nested sitemap indexes."""
    fetcher = fetcher or _Fetcher(constants.sitemap_fetch_timeout_seconds())
    max_depth = constants.sitemap_max_index_depth()
    links = []
    try:
        response = fetcher.get(sitemap_url)
    except httpx.HTTPError:
        return links
    if response.status_code != 200:
        return links
    children, page_locs = _parse_sitemap(response.text, sitemap_url)
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
