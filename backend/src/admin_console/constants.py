"""Runtime-tunable constants for the admin console (Principle XIII).

Every value is a database-backed django-constance constant declared in
``config/settings.py``; services read them through ``constance.config`` so operators can
adjust behavior at runtime without a code change (FR-043, SC-015).
"""

from constance import config


def _list(value):
    return list(value or [])


def replay_period_hours():
    return int(config.REPLAY_PERIOD_HOURS)


def replay_batch_size():
    return int(config.REPLAY_BATCH_SIZE)


def failure_rate_threshold():
    return float(config.FAILURE_RATE_THRESHOLD)


def failure_rate_window_runs():
    return int(config.FAILURE_RATE_WINDOW_RUNS)


def labeling_enabled():
    return bool(config.LABELING_ENABLED)


def labeling_config():
    return {
        "provider": str(config.LABELING_PROVIDER),
        "model": str(config.LABELING_MODEL) or None,
        "language": str(config.LABELING_LANGUAGE),
        "batch_size": int(config.LABELING_BATCH_SIZE),
    }


def sitemap_fetch_timeout_seconds():
    return int(config.SITEMAP_FETCH_TIMEOUT_SECONDS)


def sitemap_max_index_depth():
    return int(config.SITEMAP_MAX_INDEX_DEPTH)


def link_discovery_max_links():
    return int(config.LINK_DISCOVERY_MAX_LINKS)


def cleaning_rules():
    return dict(config.CLEANING_RULES or {})


def cleaning_unit_families():
    return dict(config.CLEANING_UNIT_FAMILIES or {})


def capture_modes_allowed():
    return _list(config.CAPTURE_MODES_ALLOWED)


def capture_fixed_duration_ms():
    return int(config.CAPTURE_FIXED_DURATION_MS)


def publish_auto_threshold():
    return float(config.PUBLISH_AUTO_THRESHOLD)


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
