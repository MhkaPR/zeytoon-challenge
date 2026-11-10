"""Runtime-tunable recommendation settings.

Values resolve in this order: django-constance, Django settings, module default. No
service hard-codes a weight, cap, expiry, semantic dimension, or cluster limit.
"""

from django.conf import settings

DEFAULTS = {
    "RECOMMENDATION_SIGNAL_WEIGHTS": {
        "destination_visit": 0.3,
        "details_view": 0.8,
        "search_impression": 1.5,
    },
    "RECOMMENDATION_UNCERTAINTY": 1.0,
    "RECOMMENDATION_DRIFT": 0.1,
    "RECOMMENDATION_NEGATIVE_FACTOR": 0.5,
    "RECOMMENDATION_PROFILE_TTL_DAYS": 180,
    "RECOMMENDATION_SIGNAL_CAP_PER_MINUTE": 30,
    "RECOMMENDATION_SPACE_CACHE_TTL": 3600,
    "RECOMMENDATION_N_BINS": 5,
    "RECOMMENDATION_SEMANTIC_DIMENSIONS": 10,
    "RECOMMENDATION_SEMANTIC_N_FEATURES": 1024,
    "RECOMMENDATION_SEMANTIC_NGRAM_MIN": 2,
    "RECOMMENDATION_SEMANTIC_NGRAM_MAX": 4,
    "RECOMMENDATION_SEMANTIC_RANDOM_STATE": 0,
    "RECOMMENDATION_MAX_INTEREST_CLUSTERS": 4,
    "RECOMMENDATION_CLUSTER_DISTANCE_THRESHOLD": 0.2,
    "RECOMMENDATION_CLUSTER_ACTIVITY_DECAY": 0.8,
    "RECOMMENDATION_CLUSTER_MIN_ACTIVITY": 0.0,
    "RECOMMENDATION_CLUSTER_MIN_ACTIVITY_RATIO": 0.0001,
    "RECOMMENDATION_SUGGESTION_CLUSTER_LIMIT": 3,
    "RECOMMENDATION_MIN_RESOURCE_DIMENSIONS": 1,
    "RECOMMENDATION_EXPLAIN_K": 20,
    "RECOMMENDATION_EXPLAIN_MIN_PATTERN_SIZE": 30,
    "RECOMMENDATION_EXPLAIN_ALPHA": 0.05,
    "RECOMMENDATION_EXPLAIN_MIN_LIFT": 2.0,
    "RECOMMENDATION_EXPLAIN_MIN_MCC": 0.20,
    "RECOMMENDATION_EXPLAIN_MIN_CLICKS": 3,
    "RECOMMENDATION_EXPLAIN_MESSAGES": {},
    "RECOMMENDATION_EXPLAIN_NEGATIVE_ENABLED": True,
}


def _value(name):
    try:
        from constance import config

        value = getattr(config, name)
        if value is not None:
            return value
    except Exception:
        pass
    return getattr(settings, name, DEFAULTS[name])


def signal_weights():
    return dict(_value("RECOMMENDATION_SIGNAL_WEIGHTS"))


def signal_noise(kind):
    return float(signal_weights().get(kind, 1.0))


def uncertainty():
    return float(_value("RECOMMENDATION_UNCERTAINTY"))


def drift():
    return float(_value("RECOMMENDATION_DRIFT"))


def negative_factor():
    return float(_value("RECOMMENDATION_NEGATIVE_FACTOR"))


def profile_ttl_days():
    return int(_value("RECOMMENDATION_PROFILE_TTL_DAYS"))


def signal_cap_per_minute():
    return int(_value("RECOMMENDATION_SIGNAL_CAP_PER_MINUTE"))


def space_cache_ttl():
    return int(_value("RECOMMENDATION_SPACE_CACHE_TTL"))


def n_bins():
    return int(_value("RECOMMENDATION_N_BINS"))


def semantic_dimensions():
    return int(_value("RECOMMENDATION_SEMANTIC_DIMENSIONS"))


def semantic_n_features():
    return int(_value("RECOMMENDATION_SEMANTIC_N_FEATURES"))


def semantic_ngram_range():
    return (
        int(_value("RECOMMENDATION_SEMANTIC_NGRAM_MIN")),
        int(_value("RECOMMENDATION_SEMANTIC_NGRAM_MAX")),
    )


def semantic_random_state():
    return int(_value("RECOMMENDATION_SEMANTIC_RANDOM_STATE"))


def max_interest_clusters():
    return int(_value("RECOMMENDATION_MAX_INTEREST_CLUSTERS"))


def cluster_distance_threshold():
    return float(_value("RECOMMENDATION_CLUSTER_DISTANCE_THRESHOLD"))


def cluster_activity_decay():
    return float(_value("RECOMMENDATION_CLUSTER_ACTIVITY_DECAY"))


def cluster_min_activity():
    return float(_value("RECOMMENDATION_CLUSTER_MIN_ACTIVITY"))


def cluster_min_activity_ratio():
    return float(_value("RECOMMENDATION_CLUSTER_MIN_ACTIVITY_RATIO"))


def suggestion_cluster_limit():
    return int(_value("RECOMMENDATION_SUGGESTION_CLUSTER_LIMIT"))


def min_resource_dimensions():
    return int(_value("RECOMMENDATION_MIN_RESOURCE_DIMENSIONS"))


def explain_k():
    return int(_value("RECOMMENDATION_EXPLAIN_K"))


def explain_min_pattern_size():
    return int(_value("RECOMMENDATION_EXPLAIN_MIN_PATTERN_SIZE"))


def explain_alpha():
    return float(_value("RECOMMENDATION_EXPLAIN_ALPHA"))


def explain_min_lift():
    return float(_value("RECOMMENDATION_EXPLAIN_MIN_LIFT"))


def explain_min_mcc():
    return float(_value("RECOMMENDATION_EXPLAIN_MIN_MCC"))


def explain_min_clicks():
    return int(_value("RECOMMENDATION_EXPLAIN_MIN_CLICKS"))


def explain_messages():
    return dict(_value("RECOMMENDATION_EXPLAIN_MESSAGES") or {})


def explain_negative_enabled():
    return bool(_value("RECOMMENDATION_EXPLAIN_NEGATIVE_ENABLED"))
