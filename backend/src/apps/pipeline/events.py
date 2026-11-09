"""Structured domain events for the admin console (FR-055, SC-021).

Secrets are redacted by :mod:`utils.logging`; phone numbers are not emitted by the events
in this module. Hot paths use aggregation rather than per-item logs (Principle VII
anti-noise).
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
        domain=site.domain,
        actor_id=getattr(actor, "pk", None),
    )


def links_discovered(site, discovered, after_policy, source):
    _emit(
        "ops_links_discovered",
        site_id=site.pk,
        discovered=discovered,
        after_policy=after_policy,
        source=source,
    )


def empty_discovery(site):
    _emit(
        "ops_empty_discovery",
        site_id=site.pk,
        domain=site.domain,
    )


def capture_started(link, session):
    _emit(
        "ops_capture_started", link_id=link.pk, session_id=session.pk, mode=session.mode
    )


def capture_failed(link, session, reason):
    _emit("ops_capture_failed", link_id=link.pk, session_id=session.pk, reason=reason)


def trace_stored(trace, sha256):
    _emit(
        "ops_trace_stored",
        trace_id=trace.pk,
        link_id=trace.link_id,
        sha256=sha256,
    )


def extraction_completed(link, table_count):
    _emit("ops_extraction_completed", link_id=link.pk, table_count=table_count)


def extraction_empty(link):
    _emit("ops_extraction_empty", link_id=link.pk)


def price_table_detection_completed(link, price_tables, total):
    _emit(
        "ops_price_table_detection_completed",
        link_id=link.pk,
        price_tables=price_tables,
        total=total,
    )


def plans_extracted(link, count, skipped):
    _emit("ops_plans_extracted", link_id=link.pk, count=count, skipped=skipped)


def no_price_tables_found(link, total):
    _emit("ops_no_price_tables_found", link_id=link.pk, total=total)


def labeling_run(link, call_count, tokens):
    _emit("ops_labeling_run", link_id=link.pk, call_count=call_count, tokens=tokens)


def labeling_skipped(link, reason):
    _emit("ops_labeling_skipped", link_id=link.pk, reason=reason)


def published(link, count):
    _emit("ops_published", link_id=link.pk, count=count)


def retired(link, count):
    _emit("ops_retired", link_id=link.pk, count=count)


def replay_completed(run, change_count, reextracted):
    _emit(
        "ops_replay_completed",
        replay_run_id=run.pk,
        link_id=run.link_id,
        change_count=change_count,
        reextracted=reextracted,
    )


def alert_raised(link, failure_rate):
    _emit(
        "ops_alert_raised", link_id=link.pk, failure_rate=round(float(failure_rate), 4)
    )


def stage_failed(link, stage, reason):
    _emit("ops_stage_failed", link_id=link.pk, stage=stage, reason=reason)
