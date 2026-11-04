"""Settings for the pytest suite: local caches, no external services."""

from .base import *  # noqa: F401,F403

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "torob-test-cache",
    }
}

CONSTANCE_BACKEND = "constance.backends.memory.MemoryBackend"
