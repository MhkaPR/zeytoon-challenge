"""The automated site-maintenance pipeline (spec 003).

Every stage is server-side and per-link isolated: discovery → refilter → headless
capture → table extraction → classification → plan data → publish, with compare-driven
replay on top. LLM-gated stages are gated by the admin-owned token budget; when it is
exhausted the link parks in ``awaiting_llm_budget`` and resumes later (FR-047..FR-050).
Network/provider failures are retried with backoff and dead-lettered on exhaustion
(FR-051, FR-052).
"""

import hashlib
import time
import urllib.parse
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from admin_console import (
    artifacts,
    constants,
    discovery,
    domtrack_client,
    events,
    llm,
    plan_schema,
)
from admin_console import refilter as refilter_mod
from admin_console.models import (
    CaptureSession,
    ChangeRecord,
    ExtractedTable,
    ExtractedTableColumn,
    ExtractedTableRow,
    FailureAlert,
    Link,
    PlanRecord,
    ReplayRun,
    SemanticLabel,
    Site,
    TableClassification,
    Trace,
)
_REMOTE_ERRORS = (domtrack_client.DomtrackCaptureError, OSError, TimeoutError)


def _sleep(seconds):
    time.sleep(seconds)


# ---------------------------------------------------------------------------
# US1 — approval queue (FR-001..FR-006)
# ---------------------------------------------------------------------------


def approval_queue():
    from companies.interfaces import CompaniesInterface

    return [
        CompaniesInterface.pending_approval_payload(company)
        for company in CompaniesInterface.companies_awaiting_verification()
    ]


@transaction.atomic
def record_decision(company_id, actor, outcome, note=""):
    from companies.interfaces import CompaniesInterface

    company = CompaniesInterface.company_or_error(company_id)
    decision = CompaniesInterface.record_verification_decision(
        company, actor, outcome, note=note
    )
    site = Site.objects.filter(company=company).first()
    if outcome == "approved":
        if site is None:
            site = Site.objects.create(
                company=company,
                domain=company.domain,
                maintenance_state=Site.MaintenanceState.ONBOARDING,
            )
        elif site.maintenance_state == Site.MaintenanceState.SUSPENDED:
            site.maintenance_state = Site.MaintenanceState.ONBOARDING
            site.save(update_fields=["maintenance_state", "updated_at"])
    elif site is not None:
        site.maintenance_state = Site.MaintenanceState.SUSPENDED
        site.save(update_fields=["maintenance_state", "updated_at"])
    return company, decision, site


# ---------------------------------------------------------------------------
# US2 — automated link discovery (FR-007..FR-011)
# ---------------------------------------------------------------------------


def _url_hash(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def onboard_site(company_id, actor=None):
    from companies.models import Company

    company = Company.objects.get(pk=company_id)
    site, _ = Site.objects.get_or_create(
        company=company,
        defaults={
            "domain": company.domain,
            "maintenance_state": Site.MaintenanceState.ONBOARDING,
            "onboarded_at": timezone.now(),
        },
    )
    events.site_onboarded(site, actor=actor)
    return site


def _store_links(site, urls, source):
    stored = []
    for url in urls:
        link, _ = Link.objects.get_or_create(
            site=site,
            url_hash=_url_hash(url),
            defaults={
                "url": url,
                "source": source,
                "review_state": Link.ReviewState.CANDIDATE,
                "pipeline_stage": Link.PipelineStage.DISCOVERED,
            },
        )
        stored.append(link)
    return stored


def discover_and_store_links(site, actor=None, bounds=None):
    """Adaptive crawl the site domain and store surviving links (FR-008, FR-009)."""
    host = urllib.parse.urlsplit(
        site.domain if "://" in site.domain else f"https://{site.domain}"
    ).netloc
    harvested = []
    for query in constants.link_crawl_queries():
        harvested.extend(discovery.crawl_candidate_links(site.domain, query, bounds=bounds))
    reduced = discovery.apply_link_policy(harvested, host=host)
    stored = _store_links(site, reduced, Link.Source.ADAPTIVE_CRAWL)
    events.links_discovered(
        site, len(harvested), len(reduced), Link.Source.ADAPTIVE_CRAWL
    )
    if not stored:
        _notify_empty_discovery(site)
    return {"discovered": len(harvested), "after_policy": len(reduced), "links": stored}


def _notify_empty_discovery(site):
    """Tell the operator a crawl found nothing so the site stays visible (FR-011)."""
    from notifications.interfaces import NotificationsInterface

    NotificationsInterface.notify(
        event_type="link_discovery_empty",
        subject=f"No candidate links found for {site.domain}",
        body="The adaptive crawl found no plans links; the site stays in onboarding.",
        related_object=f"admin_console.Site:{site.pk}",
        dedup_key=f"discovery-empty:{site.pk}",
    )


def add_links_manually(site, urls, actor=None):
    reduced = discovery.apply_link_policy(urls, host=None)
    stored = _store_links(site, reduced, Link.Source.MANUAL)
    events.links_discovered(site, len(urls), len(reduced), Link.Source.MANUAL)
    return stored


# ---------------------------------------------------------------------------
# US3 — LLM link refilter (FR-012..FR-015)
# ---------------------------------------------------------------------------


def refilter_link(link, actor=None, html=None):
    """Derive the page summary, ask the LLM, and persist the verdict (FR-012..FR-015)."""
    page_html = html if html is not None else refilter_mod.fetch_html(link.url)
    verdict = refilter_mod.refilter_page(
        link.url, page_html, link=link, idempotency_key=f"refilter:{link.pk}"
    )
    drop = refilter_mod.should_drop(verdict)
    link.refilter_plan_type = verdict.plan_type or ""
    link.refilter_confidence = verdict.confidence
    # Borderline (any verdict below the drop threshold that is still kept) is flagged
    # for review so a provider is never silently lost (FR-014).
    link.refilter_flag = bool(
        not drop
        and verdict.confidence < constants.refilter_drop_confidence()
    )
    link.review_state = (
        Link.ReviewState.DROPPED if drop else Link.ReviewState.KEPT
    )
    link.pipeline_stage = (
        Link.PipelineStage.DISCOVERED if drop else Link.PipelineStage.REFILTERED
    )
    link.save()
    events.refilter_verdict(
        link, link.review_state, link.refilter_plan_type, link.refilter_confidence
    )
    return link


def override_refilter(link, review_state, reason="", actor=None):
    link.review_state = review_state
    link.pipeline_stage = (
        Link.PipelineStage.REFILTERED
        if review_state == Link.ReviewState.KEPT
        else Link.PipelineStage.DISCOVERED
    )
    link.last_error = reason[:512]
    link.save()
    return link


# ---------------------------------------------------------------------------
# US4 — server-side headless capture (FR-016..FR-019)
# ---------------------------------------------------------------------------


def _materialize(trace):
    return artifacts.materialize(trace.storage_key, backend=trace.storage_backend)


def start_capture(link, actor=None, duration_ms=None):
    """Create a headless capture session and record the trace (FR-016..FR-019)."""
    if link.review_state != Link.ReviewState.KEPT:
        raise ValueError("link_not_ready")
    if link.capture_sessions.filter(
        state__in=CaptureSession.NON_TERMINAL
    ).exists():
        raise RuntimeError("capture_in_progress")
    duration = int(duration_ms or constants.capture_fixed_duration_ms())
    session = CaptureSession.objects.create(
        link=link,
        mode=CaptureSession.Mode.HEADLESS_FIXED,
        state=CaptureSession.State.RECORDING,
        duration_ms=duration,
    )
    events.capture_started(link, session)

    def _run():
        return domtrack_client.capture_headless(
            link.url, duration, constants.capture_nav_timeout_ms()
        )

    try:
        data = _run_with_retries("capture", link, _run)
    except Exception as exc:  # noqa: BLE001 - the failed attempt must be recorded
        fail_capture(session, exc)
        events.capture_failed(link, session, str(exc)[:200])
        raise

    key, backend, size, digest = artifacts.save_trace(data)
    with transaction.atomic():
        trace = Trace.objects.create(
            link=link,
            capture_session=session,
            captured_at=timezone.now(),
            origin=Trace.Origin.SERVER_CAPTURE,
            storage_key=key,
            storage_backend=backend,
            byte_size=size,
            content_sha256=digest,
            is_valid_trace=True,
        )
        session.state = CaptureSession.State.STORED
        session.trace = trace
        session.save(update_fields=["state", "trace", "updated_at"])
        link.current_trace = trace
        link.pipeline_stage = Link.PipelineStage.CAPTURED
        link.retry_count = 0
        link.last_error = ""
        link.save()
    events.trace_stored(trace, size, digest)
    return session


def fail_capture(session, error):
    session.state = CaptureSession.State.FAILED
    session.error = str(error)[:512]
    session.save(update_fields=["state", "error", "updated_at"])
    return session


# ---------------------------------------------------------------------------
# US5 — table extraction (FR-020..FR-022)
# ---------------------------------------------------------------------------


def extract_link_tables(link, actor=None):
    trace = link.current_trace
    if trace is None:
        raise Trace.DoesNotExist("trace_required")
    path = _materialize(trace)
    config = constants.table_discovery_config()
    result = domtrack_client.extract_tables(
        path, min_rows=config["min_rows"], min_cols=config["min_cols"],
        dedupe=config["dedupe"],
    )
    tables = result.get("tables") or []
    with transaction.atomic():
        ExtractedTable.objects.filter(link=link).delete()
        for index, table in enumerate(tables):
            _persist_table(link, trace, index, table)
    if tables:
        link.pipeline_stage = Link.PipelineStage.EXTRACTED
        events.extraction_completed(link, len(tables))
    else:
        link.pipeline_stage = Link.PipelineStage.FLAGGED
        events.extraction_empty(link)
    link.save()
    return tables


def _persist_table(link, trace, index, table):
    parent = (table.get("parent") or {}).get("tag", "")
    columns = table.get("columns") or []
    rows = table.get("rows") or []
    record = ExtractedTable.objects.create(
        trace=trace,
        link=link,
        table_index=index,
        parent=parent,
        score=float(table.get("score") or 0.0),
        column_count=int(table.get("column_count") or len(columns)),
        row_count=int(table.get("row_count") or len(rows)),
        meta=table.get("meta") or {},
    )
    for column in columns:
        ExtractedTableColumn.objects.create(
            table=record,
            column_id=column["id"],
            label=column.get("label") or "",
            path=column.get("path") or "",
            atype=column.get("atype") or "",
            slot="" if column.get("slot") is None else str(column.get("slot")),
            coverage=float(column.get("coverage") or 0.0),
            row_count=int(column.get("row_count") or 0),
        )
    for row_index, row in enumerate(rows):
        ExtractedTableRow.objects.create(
            table=record, row_index=row_index, cells=row
        )
    return record


def tables_payload(link):
    tables = []
    for table in link.extracted_tables.prefetch_related("columns", "rows").all():
        classification = getattr(table, "classification", None)
        tables.append(
            {
                "id": table.pk,
                "parent": table.parent,
                "score": table.score,
                "column_count": table.column_count,
                "row_count": table.row_count,
                "columns": [
                    {
                        "id": column.pk,
                        "column_id": column.column_id,
                        "label": column.label,
                        "path": column.path,
                        "atype": column.atype,
                        "coverage": column.coverage,
                    }
                    for column in table.columns.all()
                ],
                "rows": [row.cells for row in table.rows.all()],
                "classification": (
                    {
                        "is_plans_table": classification.is_plans_table,
                        "plan_type": classification.plan_type,
                        "confidence": classification.confidence,
                    }
                    if classification
                    else None
                ),
            }
        )
    return tables


def _table_context(table):
    """A compact table view for the LLM: column labels + rows (no selectors needed)."""
    columns = list(table.columns.all())
    return {
        "columns": [column.label or column.column_id for column in columns],
        "rows": [
            [row.cells.get(column.column_id, "") for column in columns]
            for row in table.rows.all()
        ],
    }


# ---------------------------------------------------------------------------
# US6 — table classification (FR-023..FR-025)
# ---------------------------------------------------------------------------


def classify_link_tables(link, actor=None):
    tables = list(link.extracted_tables.all())
    if not tables:
        raise ValueError("no_tables_found")
    contexts = [
        {"table_index": index, **_table_context(table)}
        for index, table in enumerate(tables)
    ]
    verdicts = llm.classify_tables(
        contexts, link=link, idempotency_key=f"classify:{link.pk}"
    )
    by_index = {verdict.table_index: verdict for verdict in verdicts}
    plans_count = 0
    if by_index:
        TableClassification.objects.filter(table__link=link).delete()
        for index, table in enumerate(tables):
            verdict = by_index.get(index)
            if verdict is None:
                continue
            TableClassification.objects.create(
                table=table,
                is_plans_table=verdict.is_plans_table,
                plan_type=verdict.plan_type,
                confidence=verdict.confidence,
                provider=constants.refilter_provider(),
                model=constants.refilter_model() or "",
                prompt_version=llm.PROMPT_VERSION,
            )
            if verdict.is_plans_table:
                plans_count += 1
    link.pipeline_stage = Link.PipelineStage.CLASSIFIED
    link.save()
    events.classification_completed(link, plans_count, len(tables))
    return link


def classifications_payload(link):
    results = []
    for table in link.extracted_tables.all():
        classification = getattr(table, "classification", None)
        if classification is None:
            continue
        results.append(
            {
                "table_id": table.pk,
                "is_plans_table": classification.is_plans_table,
                "plan_type": classification.plan_type,
                "confidence": classification.confidence,
            }
        )
    return results


# ---------------------------------------------------------------------------
# US7 — plan schema extraction (data, not formulas) (FR-026..FR-031)
# ---------------------------------------------------------------------------


def extract_link_plans(link, actor=None):
    tables = [
        table
        for table in link.extracted_tables.all()
        if getattr(table, "classification", None) is not None
        and table.classification.is_plans_table
    ]
    if not tables:
        raise ValueError("plans_required")
    extracted = 0
    skipped = 0
    for table in tables:
        classification = table.classification
        plan_type = classification.plan_type or "hosting"
        field_keys = plan_schema.all_field_keys(plan_type)
        plans = llm.extract_plans(
            _table_context(table),
            plan_type,
            field_keys,
            link=link,
            table=table,
            idempotency_key=f"plans:{table.pk}",
        )
        valid = [
            plan
            for plan in plans
            if _plan_is_complete(plan.values, plan_type)
        ]
        if not valid:
            skipped += 1
            continue
        with transaction.atomic():
            PlanRecord.objects.filter(table=table).delete()
            for index, plan in enumerate(valid):
                PlanRecord.objects.create(
                    link=link,
                    table=table,
                    classification=classification,
                    plan_type=plan_type,
                    natural_key=_natural_key(plan.values, plan_type, index),
                    values=plan.values,
                    confidence=plan.confidence,
                    prompt_version=llm.PROMPT_VERSION,
                )
                extracted += 1
    link.pipeline_stage = Link.PipelineStage.PLANS_EXTRACTED
    link.save()
    events.plans_extracted(link, extracted, skipped)
    return link


def _plan_is_complete(values, plan_type):
    required = plan_schema.required_keys(plan_type)
    return all(values.get(key) not in (None, "") for key in required)


def _natural_key(values, plan_type, index):
    name = values.get("plan_name") or f"{plan_type}-{index}"
    return f"{plan_type}:{name}:{index}"


def plans_payload(link):
    return [
        {
            "id": plan.pk,
            "classification_id": plan.classification_id,
            "trace_id": plan.table.trace_id,
            "plan_type": plan.plan_type,
            "natural_key": plan.natural_key,
            "values": plan.values,
            "confidence": plan.confidence,
        }
        for plan in link.plan_records.select_related("table").all()
    ]


# ---------------------------------------------------------------------------
# US8 — optional LLM labeling (FR-032..FR-035)
# ---------------------------------------------------------------------------


def label_link_tables(link, actor=None):
    if not constants.labeling_enabled():
        raise PermissionError("labeling_disabled")
    tables = list(link.extracted_tables.all())
    if not tables:
        raise ValueError("no_tables_found")
    payload = {
        "tables": [
            {"table_index": index, **_table_context(table)}
            for index, table in enumerate(tables)
        ]
    }
    result = domtrack_client.label_tables(
        payload["tables"], constants.labeling_config()
    )
    labels = []
    with transaction.atomic():
        SemanticLabel.objects.filter(table__link=link).delete()
        for index, table in enumerate(tables):
            entry = (result.get("tables") or [])
            entry = entry[index] if index < len(entry) else {}
            for column in table.columns.all():
                label = _column_label(entry, column)
                if label:
                    SemanticLabel.objects.create(
                        table=table,
                        column=column,
                        label=label,
                        provider=constants.labeling_config()["provider"],
                        model=constants.labeling_config()["model"] or "",
                        language=constants.labeling_config()["language"],
                    )
                    labels.append({"table_id": table.pk, "column_id": column.column_id,
                                   "label": label})
    events.labeling_run(link, len(tables), 0)
    return labels


def _column_label(entry, column):
    for candidate in (entry.get("columns") or []):
        if isinstance(candidate, dict) and candidate.get("id") == column.column_id:
            return candidate.get("label") or ""
    return ""


# ---------------------------------------------------------------------------
# US9 — publishing (FR-036..FR-038)
# ---------------------------------------------------------------------------


def publish_link_plans(link, actor=None):
    from catalog.interfaces import CatalogInterface

    plans = list(link.plan_records.all())
    if not plans:
        raise ValueError("plans_required")
    published = 0
    for plan in plans:
        if not _plan_is_complete(plan.values, plan.plan_type):
            continue
        CatalogInterface.upsert_published_record(
            source="admin_console",
            site=link.site_id,
            link=link.pk,
            trace=plan.table.trace_id,
            classification=plan.classification_id,
            plan_type=plan.plan_type,
            natural_key=plan.natural_key,
            values=plan.values,
        )
        published += 1
    link.pipeline_stage = Link.PipelineStage.PUBLISHED
    link.save()
    events.published(link, published)
    return published


def retire_missing_plans(link, current_keys):
    """Retire published records whose plan is no longer present (FR-038)."""
    from catalog.interfaces import CatalogInterface

    published = CatalogInterface.published_natural_keys(site=link.site_id)
    stale = [key for key in published if key not in set(current_keys)]
    count = 0
    for natural_key in stale:
        CatalogInterface.retire_published_record(
            source="admin_console", site=link.site_id, natural_key=natural_key
        )
        count += 1
    if count:
        events.retired(link, count)
    return count


# ---------------------------------------------------------------------------
# US10 — replay, failure rate, alerts, re-run (FR-039..FR-046)
# ---------------------------------------------------------------------------


def evaluate_failure_alert(link):
    threshold = constants.failure_rate_threshold()
    open_alert = link.failure_alerts.filter(state=FailureAlert.State.OPEN).first()
    if link.failure_rate >= threshold and open_alert is None:
        alert = FailureAlert.objects.create(
            link=link,
            state=FailureAlert.State.OPEN,
            failure_rate=link.failure_rate,
            raised_at=timezone.now(),
            notification_dedup_key=f"alert:{link.pk}:open",
        )
        from notifications.interfaces import NotificationsInterface

        NotificationsInterface.notify(
            event_type="link_failure_alert",
            subject=f"Link needs updating: {link.url}",
            body=f"Failure rate {link.failure_rate:.2f} crossed {threshold:.2f}.",
            related_object=f"admin_console.Link:{link.pk}",
            dedup_key=f"alert:{link.pk}:open",
        )
        events.alert_raised(link, link.failure_rate)
        return alert
    if link.failure_rate < threshold and open_alert is not None:
        open_alert.state = FailureAlert.State.RESOLVED
        open_alert.resolved_at = timezone.now()
        open_alert.save(update_fields=["state", "resolved_at", "updated_at"])
    return open_alert


def rerun_link_stages(link, actor=None):
    link.pipeline_stage = Link.PipelineStage.DISCOVERED
    link.retry_count = 0
    link.last_error = ""
    link.save()
    return link


def replay_run_payload(run):
    return {
        "id": run.pk,
        "link_id": run.link_id,
        "state": run.state,
        "scheduled_for": run.scheduled_for,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "before_trace_id": run.before_trace_id,
        "after_trace_id": run.after_trace_id,
        "diff_summary": run.diff_summary,
        "reextracted": run.reextracted,
        "stats_applied": run.stats_applied,
        "stats_skipped": run.stats_skipped,
        "stats_failed": run.stats_failed,
        "changes": [
            {
                "change_kind": change.change_kind,
                "touches_plans_table": change.touches_plans_table,
                "classification_id": change.classification_id,
                "summary": change.summary,
            }
            for change in run.changes.all()
        ],
    }


def alert_payload(alert):
    return {
        "id": alert.pk,
        "link_id": alert.link_id,
        "state": alert.state,
        "failure_rate": alert.failure_rate,
        "raised_at": alert.raised_at,
        "resolved_at": alert.resolved_at,
    }


def due_links(now=None):
    now = now or timezone.now()
    period = constants.replay_period_hours()
    cutoff = now - timedelta(hours=period)
    return list(
        Link.objects.filter(
            is_active=True,
            review_state=Link.ReviewState.KEPT,
            site__maintenance_state=Site.MaintenanceState.ACTIVE,
        )
        .filter(
            models_q_last_replay(cutoff)
        )
        .order_by("last_replay_at")[: constants.replay_batch_size()]
    )


def models_q_last_replay(cutoff):
    from django.db.models import Q

    return Q(last_replay_at__isnull=True) | Q(last_replay_at__lt=cutoff)


def due_links_for_site(site_id, now=None):
    return [link for link in due_links(now) if link.site_id == site_id]


def replay_runs(link_id=None, state=None, limit=100):
    qs = ReplayRun.objects.select_related("link").all()
    if link_id:
        qs = qs.filter(link_id=link_id)
    if state:
        qs = qs.filter(state=state)
    return list(qs[:limit])


def alerts(state=None, limit=200):
    qs = FailureAlert.objects.select_related("link").all()
    if state:
        qs = qs.filter(state=state)
    return list(qs[:limit])


def link_failure_payload(link):
    recent = list(
        ReplayRun.objects.filter(link=link).order_by("-created_at")[
            : constants.failure_rate_window_runs()
        ]
    )
    return {
        "link_id": link.pk,
        "failure_rate": link.failure_rate,
        "window_runs": len(recent),
        "threshold": constants.failure_rate_threshold(),
        "alert_state": (
            link.failure_alerts.filter(state=FailureAlert.State.OPEN).exists()
            and "open"
            or "none"
        ),
    }


def recompute_failure_rate(link):
    window = constants.failure_rate_window_runs()
    runs = list(ReplayRun.objects.filter(link=link).order_by("-created_at")[:window])
    if not runs:
        link.failure_rate = 0.0
    else:
        failed = sum(1 for run in runs if run.state == ReplayRun.State.FAILED)
        link.failure_rate = failed / len(runs)
    link.save(update_fields=["failure_rate", "updated_at"])
    evaluate_failure_alert(link)
    return link.failure_rate


def metrics_snapshot():
    from catalog.interfaces import CatalogInterface

    return {
        "links_total": Link.objects.count(),
        "links_published": Link.objects.filter(
            pipeline_stage=Link.PipelineStage.PUBLISHED
        ).count(),
        "links_awaiting_budget": Link.objects.filter(
            pipeline_stage=Link.PipelineStage.AWAITING_LLM_BUDGET
        ).count(),
        "links_dead_lettered": Link.objects.filter(
            pipeline_stage=Link.PipelineStage.DEAD_LETTERED
        ).count(),
        "open_alerts": FailureAlert.objects.filter(
            state=FailureAlert.State.OPEN
        ).count(),
        "published_records": CatalogInterface.published_count(),
        "llm_tokens_used": llm.tokens_used(),
    }


# ---------------------------------------------------------------------------
# Budget controls (T106)
# ---------------------------------------------------------------------------


def token_budget_status(scope="global", period="monthly"):
    return {
        "scope": scope,
        "period": period,
        "token_budget": llm.current_budget(scope=scope, period=period),
        "tokens_used": llm.tokens_used(scope=scope, period=period),
    }


def set_token_budget(amount, period="monthly", scope="global", actor=None):
    return llm.set_token_budget(amount, period=period, scope=scope, actor=actor)


# ---------------------------------------------------------------------------
# Resilience helper (FR-051, FR-052)
# ---------------------------------------------------------------------------


def _run_with_retries(stage, link, fn, *args, **kwargs):
    """Run ``fn`` with backoff; dead-letter the link when attempts are exhausted."""
    attempts = max(1, constants.retry_max_attempts())
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            return fn(*args, **kwargs)
        except llm.LlmBudgetExhausted:
            raise
        except Exception as exc:  # noqa: BLE001 - retried then dead-lettered
            last_error = exc
            link.retry_count = attempt
            link.last_error = str(exc)[:500]
            link.save(update_fields=["retry_count", "last_error", "updated_at"])
            events.stage_failed(link, stage, str(exc)[:200])
            if attempt < attempts:
                _sleep(constants.retry_backoff_seconds() * attempt)
    Link.objects.filter(pk=link.pk).update(
        pipeline_stage=Link.PipelineStage.DEAD_LETTERED
    )
    link.pipeline_stage = Link.PipelineStage.DEAD_LETTERED
    raise last_error
