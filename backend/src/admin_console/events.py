"""Structured, masked domain events for the admin console (FR-044, SC-018).

Reuses :mod:`utils.logging`, whose ``SensitiveDataFilter`` masks phone numbers, so no
event emitted here can leak an unmasked identifier or trace content. Hot paths use
aggregation rather than per-item logs (Principle VII anti-noise).
"""

import logging

logger = logging.getLogger(__name__)


def _emit(event, **extra):
    payload = {"event": event}
    payload.update(extra)
    logger.info(event, extra=payload)


def site_onboarded(site, actor=None):
    _emit(
        "ops_site_onboarded",
        site_id=site.pk,
        company_id=site.company_id,
        has_sitemap=site.has_sitemap,
        actor_id=getattr(actor, "pk", None),
    )


def links_discovered(site, count, source):
    _emit("ops_links_discovered", site_id=site.pk, count=count, source=source)


def links_reviewed(site, kept, removed, actor=None):
    _emit(
        "ops_links_reviewed",
        site_id=site.pk,
        kept=kept,
        removed=removed,
        actor_id=getattr(actor, "pk", None),
    )


def capture_started(link, session, actor=None):
    _emit(
        "ops_capture_started",
        link_id=link.pk,
        session_id=session.pk,
        mode=session.mode,
        actor_id=getattr(actor, "pk", None),
    )


def capture_failed(link, session, reason):
    _emit("ops_capture_failed", link_id=link.pk, session_id=session.pk, reason=reason)


def trace_stored(trace, byte_size, sha256):
    _emit(
        "ops_trace_stored",
        trace_id=trace.pk,
        link_id=trace.link_id,
        byte_size=byte_size,
        sha256=sha256,
    )


def extraction_completed(link, table_count):
    _emit("ops_extraction_completed", link_id=link.pk, table_count=table_count)


def extraction_empty(link):
    _emit("ops_extraction_empty", link_id=link.pk)


def labeling_run(link, call_count, cost):
    _emit("ops_labeling_run", link_id=link.pk, call_count=call_count, cost=float(cost))


def labeling_skipped(link, reason):
    _emit("ops_labeling_skipped", link_id=link.pk, reason=reason)


def recipe_saved(link, version, is_complete, unconnected):
    _emit(
        "ops_recipe_saved",
        link_id=link.pk,
        version=version,
        is_complete=is_complete,
        unconnected=list(unconnected),
    )


def cleaning_completed(link, cleaned_records, exception_count):
    _emit(
        "ops_cleaning_completed",
        link_id=link.pk,
        cleaned_records=cleaned_records,
        exception_count=exception_count,
    )


def published(link, published_count):
    _emit("ops_published", link_id=link.pk, published=published_count)


def replay_run_completed(link, failure_rate, staleness_seconds, state):
    _emit(
        "ops_replay_run_completed",
        link_id=link.pk,
        failure_rate=failure_rate,
        staleness_seconds=staleness_seconds,
        state=state,
    )


def alert_raised(link, failure_rate):
    _emit("ops_alert_raised", link_id=link.pk, failure_rate=failure_rate)


def alert_resolved(link):
    _emit("ops_alert_resolved", link_id=link.pk)


def approval_queue_read(count, actor=None):
    _emit("ops_approval_queue_read", count=count, actor_id=getattr(actor, "pk", None))
