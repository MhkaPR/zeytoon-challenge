"""Public interface for the catalog module (Constitution Principle V).

``admin_console`` publishes plan data only through this interface; ``catalog`` never
imports ``admin_console``. Provenance ids are opaque integers.
"""

from apps.catalog import services


class CatalogInterface:
    """The single sanctioned entry point into the catalog module."""

    @staticmethod
    def upsert_published_record(**kwargs):
        return services.upsert_published_record(**kwargs)

    @staticmethod
    def retire_published_record(**kwargs):
        return services.retire_published_record(**kwargs)

    @staticmethod
    def published_natural_keys(**kwargs):
        return services.published_natural_keys(**kwargs)

    @staticmethod
    def published_count(**kwargs):
        return services.published_count(**kwargs)


__all__ = ["CatalogInterface"]
