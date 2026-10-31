"""Runtime-tunable constants for the admin console (Principle XIII).

Every value is a database-backed django-constance constant declared in
``config/settings.py``; services read them through this module so operators can adjust
behavior at runtime without a code change (FR-054, SC-018).
"""

from constance import config
from django.conf import settings


def _list(value):
    return list(value or [])


# -- replay / alerting -------------------------------------------------------
def replay_period_hours():
    return int(config.REPLAY_PERIOD_HOURS)


def replay_batch_size():
    return int(config.REPLAY_BATCH_SIZE)


def failure_rate_threshold():
    return float(config.FAILURE_RATE_THRESHOLD)


def failure_rate_window_runs():
    return int(config.FAILURE_RATE_WINDOW_RUNS)


# -- labeling ----------------------------------------------------------------
def labeling_enabled():
    return bool(config.LABELING_ENABLED)


def labeling_config():
    return {
        "provider": str(config.LABELING_PROVIDER),
        "model": str(config.LABELING_MODEL) or None,
        "language": str(config.LABELING_LANGUAGE),
        "batch_size": int(config.LABELING_BATCH_SIZE),
        "base_url": settings.OPENAI_BASE_URL or None,
    }


# -- link discovery ----------------------------------------------------------
def link_crawl_queries():
    return [str(config.LINK_CRAWL_QUERY_FA), str(config.LINK_CRAWL_QUERY_EN)]


def link_crawl_max_pages():
    return int(config.LINK_CRAWL_MAX_PAGES)


def link_crawl_max_depth():
    return int(config.LINK_CRAWL_MAX_DEPTH)


def link_crawl_top_k():
    return int(config.LINK_CRAWL_TOP_K)


def link_deny_extensions():
    return [str(e) for e in _list(config.LINK_DENY_EXTENSIONS)]


def link_deny_segments():
    return [str(s) for s in _list(config.LINK_DENY_SEGMENTS)]


def link_discovery_max_links():
    return int(config.LINK_DISCOVERY_MAX_LINKS)


# -- refilter ----------------------------------------------------------------
def refilter_provider():
    return str(config.REFILTER_PROVIDER)


def refilter_model():
    return str(config.REFILTER_MODEL) or None


def refilter_drop_confidence():
    return float(config.REFILTER_DROP_CONFIDENCE)


# -- capture -----------------------------------------------------------------
def capture_fixed_duration_ms():
    return int(config.CAPTURE_FIXED_DURATION_MS)


def capture_nav_timeout_ms():
    return int(config.CAPTURE_NAV_TIMEOUT_MS)


# -- resilience --------------------------------------------------------------
def retry_max_attempts():
    return int(config.RETRY_MAX_ATTEMPTS)


def retry_backoff_seconds():
    return float(config.RETRY_BACKOFF_SECONDS)


def publish_auto_threshold():
    return float(config.PUBLISH_AUTO_THRESHOLD)


# -- tables / replay ---------------------------------------------------------
def table_discovery_config():
    return {
        "min_rows": int(config.TABLE_DISCOVERY_MIN_ROWS),
        "min_cols": int(config.TABLE_DISCOVERY_MIN_COLS),
        "dedupe": bool(config.TABLE_DISCOVERY_DEDUPE),
    }


def replay_config():
    return {
        "mode": str(config.REPLAY_MODE),
        "speed": float(config.REPLAY_SPEED),
        "time_policy": str(config.REPLAY_TIME_POLICY),
        "third_party_detection": bool(config.REPLAY_THIRD_PARTY_DETECTION),
    }
