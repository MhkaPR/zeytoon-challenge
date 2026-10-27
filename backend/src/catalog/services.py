"""Write path for published plan records (FR-034..FR-036).

``upsert_published_record`` and ``retire_published_record`` are the only sanctioned ways
to mutate :class:`catalog.models.PublishedRecord`. The caller (``admin_console``) passes
already-validated payloads and opaque provenance ids.
"""

from django.utils import timezone

from catalog.models import PublishedRecord


def upsert_published_record(
    *,
    site,
    link,
    trace,
    recipe,
    plan_type,
    natural_key,
    values,
    cleaning_exceptions=None,
    source="admin_console",
):
    """Insert or update the record keyed by ``(source, site, natural_key)`` (FR-035)."""
    record, _ = PublishedRecord.objects.update_or_create(
        source=source,
        site=site,
        natural_key=natural_key,
        defaults={
            "link": link,
            "trace": trace,
            "recipe": recipe,
            "plan_type": plan_type,
            "values": values or {},
            "cleaning_exceptions": cleaning_exceptions or {},
            "is_published": True,
            "published_at": timezone.now(),
            "retired_at": None,
        },
    )
    return record


def retire_published_record(*, site, natural_key, source="admin_console"):
    """Retire a removed item so stale values are never retained (FR-036)."""
    updated = PublishedRecord.objects.filter(
        source=source, site=site, natural_key=natural_key, is_published=True
    ).update(is_published=False, retired_at=timezone.now())
    return updated
