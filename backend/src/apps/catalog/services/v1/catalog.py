"""Write path for published plan records (FR-036..FR-038).

``upsert_published_record`` and ``retire_published_record`` are the only sanctioned ways
to mutate :class:`catalog.models.PublishedRecord`. The caller (``admin_console``) passes
already-validated payloads and opaque provenance ids.
"""

from django.utils import timezone

from apps.catalog.models import PublishedRecord


def upsert_published_record(
    *,
    site,
    link,
    trace,
    classification,
    plan_type,
    natural_key,
    values,
    source="admin_console",
):
    """Insert or update the record keyed by ``(source, site, natural_key)`` (FR-037)."""
    record, _ = PublishedRecord.objects.update_or_create(
        source=source,
        site=site,
        natural_key=natural_key,
        defaults={
            "link": link,
            "trace": trace,
            "classification": classification,
            "plan_type": plan_type,
            "values": values or {},
            "is_published": True,
            "published_at": timezone.now(),
            "retired_at": None,
        },
    )
    return record


def retire_published_record(*, site, natural_key, source="admin_console"):
    """Retire a removed item so stale values are never retained (FR-038)."""
    updated = PublishedRecord.objects.filter(
        source=source, site=site, natural_key=natural_key, is_published=True
    ).update(is_published=False, retired_at=timezone.now())
    return updated


def published_natural_keys(*, site, source="admin_console", is_published=True):
    """The natural keys currently published for a site (FR-038)."""
    return list(
        PublishedRecord.objects.filter(
            source=source, site=site, is_published=is_published
        ).values_list("natural_key", flat=True)
    )


def published_count(*, source=None, is_published=True):
    """How many published records exist, optionally scoped to one source (FR-045)."""
    qs = PublishedRecord.objects.filter(is_published=is_published)
    if source is not None:
        qs = qs.filter(source=source)
    return qs.count()
