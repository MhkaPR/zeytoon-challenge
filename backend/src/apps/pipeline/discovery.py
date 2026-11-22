"""Adaptive link discovery via crawl4ai (FR-008, FR-009)."""

import asyncio
import os
import urllib.parse

from apps.pipeline import constants


class LinkDiscoverer:
    """Adaptive crawling + the deterministic same-host/deny-list policy."""

    def crawl_candidate_links(self, domain, query, bounds=None):
        bounds = bounds or {}

        resolved = {
            "max_depth": int(
                bounds.get("max_depth") or constants.link_crawl_max_depth()
            ),
            "max_pages": int(
                bounds.get("max_pages") or constants.link_crawl_max_pages()
            ),
            "top_k_links": int(
                bounds.get("top_k_links") or constants.link_crawl_top_k()
            ),
        }

        return asyncio.run(self._crawl(domain, query, resolved))

    async def _crawl(self, domain, query, resolved):
        from crawl4ai import AsyncWebCrawler, BrowserConfig
        from crawl4ai.adaptive_crawler import AdaptiveConfig, AdaptiveCrawler

        seed = domain if "://" in domain else f"https://{domain}"

        config = AdaptiveConfig(
            strategy="statistical",
            max_depth=resolved["max_depth"],
            max_pages=resolved["max_pages"],
            top_k_links=resolved["top_k_links"],
        )

        cdp_url = os.getenv("CRAWL4AI_CDP_URL")

        browser_config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            cdp_url=cdp_url,
        ) if cdp_url else BrowserConfig(
            browser_type="chromium",
            headless=True,
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            adaptive = AdaptiveCrawler(crawler, config)
            state = await adaptive.digest(
                start_url=seed,
                query=query,
            )
            return list(getattr(state, "crawled_urls", []) or [])

    def apply_link_policy(
        self, urls, deny_extensions=None, deny_segments=None, host=None, max_links=None
    ):
        deny_extensions = (
            constants.link_deny_extensions()
            if deny_extensions is None
            else deny_extensions
        )
        deny_segments = (
            constants.link_deny_segments()
            if deny_segments is None
            else deny_segments
        )
        max_links = max_links or constants.link_discovery_max_links()

        seen = set()
        result = []

        for raw in urls:
            if not raw:
                continue

            parts = urllib.parse.urlsplit(
                raw if "://" in raw else f"https://{raw}"
            )

            if parts.scheme not in ("http", "https") or not parts.netloc:
                continue

            if host and parts.netloc.lower() != host.lower():
                continue

            path = parts.path or "/"
            segments = [s for s in path.split("/") if s]

            if self._deny_extension(path, deny_extensions):
                continue

            if self._deny_segment(segments, deny_segments):
                continue

            normalized = urllib.parse.urlunsplit(
                (
                    parts.scheme.lower(),
                    parts.netloc.lower(),
                    path,
                    "",
                    "",
                )
            )

            if normalized in seen:
                continue

            seen.add(normalized)
            result.append(normalized)

            if len(result) >= max_links:
                break

        return result

    @staticmethod
    def _deny_extension(path, deny_extensions):
        tail = path.rsplit("/", 1)[-1]

        if "." not in tail:
            return False

        denied = {e.lower() for e in deny_extensions}
        return tail.rsplit(".", 1)[-1].lower() in denied

    @staticmethod
    def _deny_segment(segments, deny_segments):
        denied = {s.lower() for s in deny_segments}
        return any(segment.lower() in denied for segment in segments)


default_discoverer = LinkDiscoverer()


def crawl_candidate_links(domain, query, bounds=None):
    return default_discoverer.crawl_candidate_links(domain, query, bounds)


def apply_link_policy(
    urls, deny_extensions=None, deny_segments=None, host=None, max_links=None
):
    return default_discoverer.apply_link_policy(
        urls, deny_extensions, deny_segments, host, max_links
    )