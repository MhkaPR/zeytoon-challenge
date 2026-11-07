"""Runtime-tunable recommendation settings.

Values resolve in this order: django-constance, Django settings, module default. No
service hard-codes a weight, cap, or expiry.
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
