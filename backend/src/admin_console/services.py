"""Domain services for the operator console (approvals + site maintenance pipeline)."""

import re

from django.db import IntegrityError, transaction
from django.utils import timezone
from datetime import timedelta

from accounts.exceptions import ApiError
from admin_console import constants, events
from admin_console.models import (
    CaptureSession,
    ExtractedTable,
    ExtractedTableColumn,
    ExtractedTableRow,
    ExtractionRecipe,
    FailureAlert,
    Link,
    LlmCostLedger,
    RecipeFieldBinding,
    ReplayRun,
    SemanticLabel,
    Site,
    Trace,
)
from companies.interfaces import CompaniesInterface


# ---------------------------------------------------------------------------
# US1 — approval queue and decisions (FR-001..FR-006)
# ---------------------------------------------------------------------------


def approval_queue():
    """Return approval-queue rows for companies awaiting verification (FR-001)."""
    return [
        CompaniesInterface.pending_approval_payload(company)
        for company in CompaniesInterface.companies_awaiting_verification()
    ]


@transaction.atomic
def record_decision(company_id, actor, outcome, note=""):
    """Record one decision and drive the site lifecycle (FR-002, FR-003, FR-006).

    Delegates to ``companies`` so the append-only ``VerificationDecision`` keeps its
    single owner; the site is created (approved) or suspended (not approved).
    """
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
# US2 — site onboarding and link review (FR-007..FR-011)
# ---------------------------------------------------------------------------


def _url_hash(url):
    import hashlib

    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


@transaction.atomic
def onboard_site(company_id, actor):
    """Create the company's single site, refusing a second one (FR-007)."""
    company = CompaniesInterface.company_or_error(company_id)
    if not company.is_verified:
        raise ApiError(
            "link_not_ready",
            "The company must be approved before its site can be onboarded.",
            http_status=403,
        )
    if Site.objects.filter(company=company).exists():
        raise ApiError(
            "invalid_field",
            "This company already has a site.",
            http_status=409,
            fields={"company_id": "already onboarded"},
        )
    site = Site.objects.create(
        company=company,
        domain=company.domain,
        maintenance_state=Site.MaintenanceState.ONBOARDING,
    )
    events.site_onboarded(site, actor=actor)
    return site


def _store_links(site, urls, source, max_links):
    created = 0
    for url in urls:
        if created >= max_links:
            break
        url = (url or "").strip()
        if not url:
            continue
        _, was_created = Link.objects.get_or_create(
            site=site,
            url_hash=_url_hash(url),
            defaults={
                "url": url,
                "source": source,
                "review_state": Link.ReviewState.CANDIDATE,
                "pipeline_stage": Link.PipelineStage.REVIEW,
            },
        )
        if was_created:
            created += 1
    return created


@transaction.atomic
def discover_and_store_links(site, actor):
    """Discover candidate links from the site's sitemap and store them (FR-008)."""
    from admin_console import discovery, domtrack_client  # noqa: F401

    sitemap_url, urls = discovery.discover_site_links(site.domain)
    site.has_sitemap = bool(sitemap_url)
    site.sitemap_url = sitemap_url or ""
    site.save(update_fields=["has_sitemap", "sitemap_url", "updated_at"])
    created = _store_links(
        site, urls, Link.Source.SITEMAP, constants.link_discovery_max_links()
    )
    events.links_discovered(site, created, "sitemap")
    return {"has_sitemap": site.has_sitemap, "sitemap_url": site.sitemap_url, "discovered": created}


@transaction.atomic
def add_links_manually(site, urls, actor):
    """Store operator-entered links when no sitemap is available (FR-008)."""
    created = _store_links(
        site, urls, Link.Source.MANUAL, constants.link_discovery_max_links()
    )
    events.links_discovered(site, created, "manual")
    return {"discovered": created, "source": "manual"}


def review_links(site, keep_ids, remove_ids, actor):
    """Apply keep/remove review; removed links stay recorded (FR-009, FR-010).

    When no link is kept the site stays at ``onboarding`` with ``link_not_ready``
    (FR-011).
    """
    with transaction.atomic():
        if keep_ids:
            Link.objects.filter(site=site, pk__in=keep_ids).update(
                review_state=Link.ReviewState.KEPT,
                pipeline_stage=Link.PipelineStage.CAPTURE,
                updated_at=timezone.now(),
            )
        if remove_ids:
            Link.objects.filter(site=site, pk__in=remove_ids).update(
                review_state=Link.ReviewState.REMOVED,
                pipeline_stage=Link.PipelineStage.REVIEW,
                is_active=False,
                updated_at=timezone.now(),
            )

    kept = Link.objects.filter(
        site=site, review_state=Link.ReviewState.KEPT
    ).count()
    removed = Link.objects.filter(
        site=site, review_state=Link.ReviewState.REMOVED
    ).count()
    if kept == 0:
        events.links_reviewed(site, kept, removed, actor=actor)
        raise ApiError(
            "link_not_ready",
            "No usable links were kept; the site stays in onboarding.",
            fields={"site_id": site.pk},
        )
    site.maintenance_state = Site.MaintenanceState.ACTIVE
    site.onboarded_at = site.onboarded_at or timezone.now()
    site.save(update_fields=["maintenance_state", "onboarded_at", "updated_at"])
    events.links_reviewed(site, kept, removed, actor=actor)
    return {"kept": kept, "removed": removed, "maintenance_state": site.maintenance_state}


# ---------------------------------------------------------------------------
# US3 — operator-driven capture (FR-012..FR-017)
# ---------------------------------------------------------------------------


def start_capture(link, operator, mode="interactive", duration_ms=None):
    """Trigger domtrack capture locally for a kept link (FR-012, FR-013, FR-017)."""
    from admin_console import domtrack_client

    if mode not in constants.capture_modes_allowed():
        raise ApiError(
            "invalid_field",
            "This capture mode is not allowed.",
            fields={"mode": mode},
        )
    if link.review_state != Link.ReviewState.KEPT:
        raise ApiError(
            "link_not_ready",
            "Only kept links can be captured.",
        )
    if not duration_ms:
        duration_ms = (
            constants.capture_fixed_duration_ms()
            if mode == "fixed_duration"
            else constants.capture_interactive_duration_ms()
        )

    # Only an explicit button press starts a capture; a link reaching the capture stage
    # never records on its own. One operator may record only one link at a time.
    try:
        with transaction.atomic():
            existing = (
                CaptureSession.objects.select_for_update()
                .filter(
                    operator=operator,
                    state__in=CaptureSession.NON_TERMINAL,
                )
                .first()
            )
            if existing is not None:
                raise ApiError(
                    "capture_in_progress",
                    "You already have a capture in progress; finish it first.",
                    http_status=409,
                    fields={"capture_id": existing.pk, "link_id": existing.link_id},
                )
            session = CaptureSession.objects.create(
                link=link,
                operator=operator,
                mode=mode,
                duration_ms=duration_ms,
                state=CaptureSession.State.PENDING,
            )
    except IntegrityError as exc:
        # Two concurrent presses: the per-operator constraint wins the race.
        raise ApiError(
            "capture_in_progress",
            "You already have a capture in progress; finish it first.",
            http_status=409,
        ) from exc
    try:
        result = domtrack_client.start_local_capture(
            link.url, mode=mode, duration_ms=duration_ms
        )
    except domtrack_client.DomtrackUnreachable as exc:
        # Record the failed attempt (not deleted, FR-014/FR-017) in its own transaction
        # so the error path below can raise without rolling it back.
        with transaction.atomic():
            session.state = CaptureSession.State.FAILED
            session.error = str(exc)[:512]
            session.save(update_fields=["state", "error", "updated_at"])
            events.capture_failed(link, session, "domtrack_unreachable")
        raise ApiError(
            "domtrack_unreachable",
            "The local domtrack service could not be reached.",
            http_status=502,
        ) from exc

    with transaction.atomic():
        session.state = CaptureSession.State.AWAITING_UPLOAD
        session.local_path = str(
            result.get("json_path") or result.get("local_trace_path") or ""
        )
        session.save(update_fields=["state", "local_path", "updated_at"])
        events.capture_started(link, session, actor=operator)
    return session, result


def active_capture_for(operator):
    """The operator's unfinished capture, if any (one at a time, FR-012)."""
    return (
        CaptureSession.objects.filter(
            operator=operator, state__in=CaptureSession.NON_TERMINAL
        )
        .select_related("link")
        .first()
    )


def _sha256(data):
    import hashlib

    return hashlib.sha256(data).hexdigest()


@transaction.atomic
def store_trace(capture_session, file_or_path, operator):
    """Validate and store a trace artifact, then advance the link (FR-015, FR-016)."""
    from admin_console import artifacts, domtrack_client

    import os
    import tempfile

    if hasattr(file_or_path, "read"):
        data = file_or_path.read()
        if isinstance(data, str):
            data = data.encode("utf-8")
        tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=".json", delete=False)
        tmp.write(data)
        tmp.close()
        local_path = tmp.name
    else:
        local_path = os.path.abspath(os.path.expanduser(str(file_or_path)))
        try:
            with open(local_path, "rb") as handle:
                data = handle.read()
        except OSError as exc:
            raise ApiError(
                "invalid_field",
                "The domtrack trace path could not be read on this machine.",
                fields={"local_path": local_path, "error": str(exc)[:200]},
            ) from exc

    try:
        raw, is_valid = domtrack_client.load_trace(local_path)
    except Exception as exc:
        raise ApiError(
            "invalid_field",
            "The uploaded file is not a valid domtrack trace.",
            fields={"trace": str(exc)[:200]},
        ) from exc
    if not is_valid:
        raise ApiError(
            "invalid_field",
            "The uploaded file is not a valid domtrack trace.",
            fields={"trace": "invalid trace"},
        )

    key, backend, size, digest = artifacts.save_trace(data)
    trace = Trace.objects.create(
        link=capture_session.link,
        capture_session=capture_session,
        captured_by=operator,
        captured_at=timezone.now(),
        origin=Trace.Origin.OPERATOR_CAPTURE,
        storage_key=key,
        storage_backend=backend,
        byte_size=size,
        content_sha256=digest,
        is_valid_trace=True,
    )
    capture_session.state = CaptureSession.State.STORED
    capture_session.trace = trace
    capture_session.save(update_fields=["state", "trace", "updated_at"])

    link = capture_session.link
    link.current_trace = trace
    # The link stays at the ``capture`` stage: extraction (US4) is what advances it to
    # ``extracted``, and it is blocked while ``current_trace`` is null (FR-014).
    link.pipeline_stage = Link.PipelineStage.CAPTURE
    link.save(update_fields=["current_trace", "pipeline_stage", "updated_at"])
    events.trace_stored(trace, size, digest)
    return trace


@transaction.atomic
def fail_capture(capture_session, error):
    """Record a failed capture attempt (FR-017); the link does not advance."""
    capture_session.state = CaptureSession.State.FAILED
    capture_session.error = str(error)[:512]
    capture_session.save(update_fields=["state", "error", "updated_at"])
    events.capture_failed(capture_session.link, capture_session, "failed")
    return capture_session


# ---------------------------------------------------------------------------
# US4 — table extraction (FR-018..FR-020)
# ---------------------------------------------------------------------------


@transaction.atomic
def extract_tables_for_link(link, actor=None):
    """Extract tables from the link's stored trace via domtrack (FR-018..FR-020)."""
    from admin_console import artifacts, domtrack_client

    if link.current_trace is None:
        raise ApiError(
            "trace_required",
            "A stored trace is required before extraction.",
            http_status=409,
        )
    trace = link.current_trace
    config = constants.table_discovery_config()
    local_path = artifacts.materialize(
        trace.storage_key, backend=trace.storage_backend
    )
    result = domtrack_client.extract_tables(
        local_path,
        min_rows=config["min_rows"],
        min_cols=config["min_cols"],
        dedupe=config["dedupe"],
    )

    # Re-run replaces the previous extraction for this trace (FR-019 determinism).
    ExtractedTable.objects.filter(link=link, trace=trace).delete()

    tables = result.get("tables") or []
    for index, table in enumerate(tables):
        parent = table.get("parent") or {}
        parent_str = (
            parent.get("id") if isinstance(parent, dict) else parent
        ) or ""
        record = ExtractedTable.objects.create(
            trace=trace,
            link=link,
            table_index=index,
            parent=str(parent_str),
            score=float(table.get("score") or 0.0),
            column_count=int(table.get("column_count") or len(table.get("columns") or [])),
            row_count=int(table.get("row_count") or len(table.get("rows") or [])),
            meta=table.get("meta") or {},
        )
        for column in table.get("columns") or []:
            ExtractedTableColumn.objects.create(
                table=record,
                column_id=str(column.get("id")),
                label=column.get("label") or "",
                path=column.get("path") or "",
                atype=column.get("atype") or "",
                slot=str(column.get("slot") or ""),
                coverage=float(column.get("coverage") or 0.0),
                row_count=int(column.get("row_count") or 0),
            )
        for row_index, row in enumerate(table.get("rows") or []):
            ExtractedTableRow.objects.create(
                table=record, row_index=row_index, cells=row
            )

    if tables:
        link.pipeline_stage = Link.PipelineStage.EXTRACTED
        link.save(update_fields=["pipeline_stage", "updated_at"])
        events.extraction_completed(link, len(tables))
    else:
        link.pipeline_stage = Link.PipelineStage.FLAGGED
        link.save(update_fields=["pipeline_stage", "updated_at"])
        events.extraction_empty(link)
    return {"table_count": len(tables), "pipeline_stage": link.pipeline_stage}


def tables_payload(link):
    """Serialize the link's current extracted tables for the workspace (FR-025)."""
    trace = link.current_trace
    if trace is None:
        return []
    payload = []
    tables = ExtractedTable.objects.filter(link=link, trace=trace).prefetch_related(
        "columns__semantic_labels", "semantic_labels", "rows"
    )
    for table in tables:
        table_labels = list(table.semantic_labels.all())
        title = next((label.table_title for label in table_labels if label.table_title), "")
        purpose = next(
            (label.table_purpose for label in table_labels if label.table_purpose), ""
        )
        payload.append(
            {
                "id": table.pk,
                "score": table.score,
                "row_count": table.row_count,
                "column_count": table.column_count,
                "parent": table.parent,
                "meta": table.meta,
                "title": title,
                "purpose": purpose,
                "columns": [
                    {
                        "id": column.pk,
                        "column_id": column.column_id,
                        "label": column.label,
                        "path": column.path,
                        "atype": column.atype,
                        "slot": column.slot,
                        "coverage": column.coverage,
                        "row_count": column.row_count,
                        "labels": [
                            label.label
                            for label in column.semantic_labels.all()
                            if label.label
                        ],
                    }
                    for column in table.columns.all()
                ],
                "rows": [
                    {"row_index": row.row_index, "cells": row.cells}
                    for row in table.rows.all()
                ],
            }
        )
    return payload


# ---------------------------------------------------------------------------
# US5 — optional LLM labeling + cost ceiling (FR-021..FR-024)
# ---------------------------------------------------------------------------


def _period_bounds(period, now):
    if period == LlmCostLedger.Period.DAILY:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start
    if period == LlmCostLedger.Period.MONTHLY:
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return None


def llm_ceiling_record(scope="global"):
    """Return the current ceiling row for a scope, or ``None`` when unset."""
    return (
        LlmCostLedger.objects.filter(scope=scope, ceiling_amount__isnull=False)
        .order_by("-updated_at")
        .first()
    )


def llm_spend_total(scope="global", period=None):
    from django.db.models import Sum

    now = timezone.now()
    queryset = LlmCostLedger.objects.filter(scope=scope, amount__isnull=False)
    if period:
        start = _period_bounds(period, now)
        if start is not None:
            queryset = queryset.filter(timestamp__gte=start)
    return float(queryset.aggregate(total=Sum("amount")).get("total") or 0)


def llm_ceiling_status(scope="global"):
    """Return ``{ceiling, period, spend, exceeded}`` for the scope (Principle II)."""
    record = llm_ceiling_record(scope)
    if record is None:
        return {"ceiling": None, "period": None, "spend": 0.0, "exceeded": False}
    spend = llm_spend_total(scope, record.period)
    ceiling = float(record.ceiling_amount)
    return {
        "ceiling": ceiling,
        "period": record.period,
        "spend": spend,
        "exceeded": spend >= ceiling,
    }


def record_llm_cost(amount, link=None, scope="global", actor=None):
    """Append a spend row so the period total is observable (Principle II, FR-024)."""
    return LlmCostLedger.objects.create(
        scope=scope,
        amount=amount,
        timestamp=timezone.now(),
        label_run_ref=link,
        updated_by=actor,
    )


def set_llm_ceiling(amount, period="monthly", scope="global", actor=None):
    record = llm_ceiling_record(scope)
    if record is None:
        record = LlmCostLedger(scope=scope)
    record.ceiling_amount = amount
    record.period = period
    record.updated_by = actor
    record.save()
    return record


def assert_labeling_allowed(link, estimated_cost=0.01):
    """Refuse labeling when disabled or when the ceiling would be exceeded (FR-021, FR-024)."""
    if not constants.labeling_enabled():
        raise ApiError(
            "labeling_disabled",
            "LLM labeling is disabled.",
            http_status=403,
        )
    status = llm_ceiling_status()
    if status["ceiling"] is not None and (status["spend"] + estimated_cost) > status["ceiling"]:
        # Stop and report, write nothing, and raise a breach notification.
        from notifications.interfaces import NotificationsInterface

        NotificationsInterface.notify(
            event_type="llm_ceiling_exceeded",
            subject="LLM cost ceiling exceeded",
            body="Labeling was stopped because the configured LLM cost ceiling was reached.",
            severity=NotificationsInterface.Severity.CRITICAL,
            related_object=f"admin_console.Link:{link.pk}",
            dedup_key=f"llm_ceiling_exceeded:{link.pk}",
        )
        events.labeling_skipped(link, "llm_ceiling_exceeded")
        raise ApiError(
            "llm_ceiling_exceeded",
            "The labeling call would exceed the configured LLM cost ceiling.",
            http_status=409,
        )
    return status


def label_tables_for_link(link, actor_id=None, estimated_cost=0.01):
    """Label tables via domtrack, gated by the toggle and the LLM ceiling (FR-021..FR-024)."""
    from admin_console import domtrack_client

    assert_labeling_allowed(link, estimated_cost=estimated_cost)

    trace = link.current_trace
    if trace is None:
        raise ApiError("trace_required", "A stored trace is required.", http_status=409)
    with transaction.atomic():
        config = constants.labeling_config()
        tables = tables_payload(link)
        raw_tables = [
            {
                "id": t["id"],
                "columns": [
                    {"id": c["column_id"], "label": c["label"], "path": c["path"]}
                    for c in t["columns"]
                ],
                "rows": [r["cells"] for r in t["rows"]],
            }
            for t in tables
        ]
        result = domtrack_client.label_tables(raw_tables, config)

        call_count = 1
        labeled = result.get("tables") if isinstance(result, dict) else None
        if labeled:
            # Persist labels keyed by the returned table order.
            for index, table in enumerate(tables):
                labeled_table = labeled[index] if index < len(labeled) else {}
                table_obj = ExtractedTable.objects.get(pk=table["id"])
                SemanticLabel.objects.filter(table=table_obj).delete()
                meta = labeled_table.get("meta") or {}
                SemanticLabel.objects.create(
                    table=table_obj,
                    table_title=meta.get("title", "") or "",
                    table_purpose=meta.get("purpose", "") or "",
                    provider=config["provider"],
                    model=config.get("model") or "",
                )
                columns = list(table_obj.columns.all())
                for column_index, column in enumerate(
                    labeled_table.get("columns", []) or []
                ):
                    source_column = (
                        columns[column_index] if column_index < len(columns) else None
                    )
                    SemanticLabel.objects.create(
                        table=table_obj,
                        column=source_column,
                        label=column.get("semantic_label") or "",
                        provider=config["provider"],
                        model=config.get("model") or "",
                    )
        record_llm_cost(estimated_cost, link=link)
    events.labeling_run(link, call_count, estimated_cost)
    return {"labeled": bool(labeled), "call_count": call_count, "cost": estimated_cost}


# ---------------------------------------------------------------------------
# US6 — merge and mapping to the plan schema (FR-025..FR-031)
# ---------------------------------------------------------------------------


def get_current_recipe(link):
    """Return the link's current recipe (or ``None``) for restore (FR-031)."""
    return (
        ExtractionRecipe.objects.filter(link=link, is_current=True)
        .prefetch_related("bindings")
        .first()
    )


def recipe_payload(recipe):
    if recipe is None:
        return None
    return {
        "id": recipe.pk,
        "link_id": recipe.link_id,
        "site_id": recipe.link.site_id,
        "plan_type": recipe.plan_type,
        "version": recipe.version,
        "is_complete": recipe.is_complete,
        "bindings": [
            {
                "schema_field_key": b.schema_field_key,
                "source_table_id": b.source_table_id,
                "source_column_id": b.source_column_id,
                "selector": b.selector,
                "formula": b.formula,
                "aggregation": b.aggregation,
            }
            for b in recipe.bindings.all()
        ],
    }


@transaction.atomic
def save_recipe(link, plan_type, bindings, actor=None):
    """Validate and save a new recipe version; map the link only when complete (FR-028, FR-030)."""
    from admin_console import formulas
    from admin_console.plan_schema import PLAN_SCHEMA, required_keys

    if plan_type not in PLAN_SCHEMA:
        raise ApiError(
            "invalid_field",
            "Unknown plan type.",
            fields={"plan_type": plan_type},
        )
    field_keys = set(PLAN_SCHEMA[plan_type].field_map())
    valid_columns = {
        column.pk: column
        for column in ExtractedTableColumn.objects.filter(table__link=link)
    }

    validated = []
    for binding in bindings:
        key = binding.get("schema_field_key")
        if key not in field_keys:
            raise ApiError(
                "invalid_field",
                "Unknown schema field.",
                fields={"fields": [key]},
            )
        column_id = binding.get("source_column_id")
        column = valid_columns.get(column_id)
        if column_id is not None and column is None:
            raise ApiError(
                "invalid_field",
                "Unknown source column.",
                fields={"fields": [f"source_column_id:{column_id}"]},
            )
        formula = formulas.validate_formula(binding.get("formula", ""))
        selector = binding.get("selector") or (column.path if column else "")
        validated.append((key, column, selector, formula, binding.get("aggregation", "")))

    required = required_keys(plan_type)
    connected = {key for key, *_ in validated if key in required}
    unconnected = sorted(required - connected)
    is_complete = not unconnected

    version = (
        ExtractionRecipe.objects.filter(link=link).order_by("-version").first()
    )
    next_version = (version.version + 1) if version else 1
    ExtractionRecipe.objects.filter(link=link, is_current=True).update(
        is_current=False, updated_at=timezone.now()
    )
    recipe = ExtractionRecipe.objects.create(
        link=link,
        plan_type=plan_type,
        version=next_version,
        is_current=True,
        is_complete=is_complete,
    )
    for key, column, selector, formula, aggregation in validated:
        RecipeFieldBinding.objects.create(
            recipe=recipe,
            schema_field_key=key,
            source_table=column.table if column else None,
            source_column=column,
            selector=selector,
            formula=formula,
            aggregation=aggregation or "",
        )

    if is_complete:
        link.pipeline_stage = Link.PipelineStage.MAPPED
        link.save(update_fields=["pipeline_stage", "updated_at"])
    events.recipe_saved(link, next_version, is_complete, unconnected)
    return recipe, unconnected


# ---------------------------------------------------------------------------
# US7 — cleaning and publishing (FR-032..FR-036)
# ---------------------------------------------------------------------------


def _recipe_row_values(link, recipe):
    """Evaluate the current recipe over the link's extracted rows (FR-029, no re-mapping).

    Returns a list of ``(natural_key, {schema_field_key: value})`` items, one per source
    table row. Formula references resolve against ``{column_id: value}`` plus the column
    path/label so an operator-written formula (``=A2``, ``=Price*2``) binds to the row.
    """
    from admin_console import formulas

    recipe_by_key = {}
    for binding in recipe.bindings.select_related("source_table", "source_column"):
        recipe_by_key[binding.schema_field_key] = binding

    tables = {
        table.pk: table
        for table in ExtractedTable.objects.filter(link=link, trace=link.current_trace)
        .prefetch_related("columns")
    }
    # Each distinct source table is turned into a positional context so Excel-style
    # references (``A2``, ``B2:B9``) and named columns (``Price``) both resolve.
    contexts = {}
    for table_id in {
        b.source_table_id for b in recipe_by_key.values() if b.source_table_id
    }:
        table = tables.get(table_id)
        if table is not None:
            contexts[table_id] = _table_context(table)

    # Pre-resolve every free reference a binding formula uses, once per table.
    refs_by_table = {}
    for binding in recipe_by_key.values():
        if not binding.source_table_id or not binding.formula:
            continue
        refs_by_table.setdefault(binding.source_table_id, set()).update(
            formulas.references(binding.formula)
        )

    # Row count/order comes from the primary source table (the first bound field's table).
    primary_id = next(
        (b.source_table_id for b in recipe_by_key.values() if b.source_table_id), None
    )
    primary_context = contexts.get(primary_id)
    primary_rows = primary_context["rows"] if primary_context else []

    items = []
    for position, row_index in enumerate(primary_rows):
        values = {}
        for field_key, binding in recipe_by_key.items():
            context = contexts.get(binding.source_table_id)
            if context is None:
                context = primary_context
            position_for_table = (
                position
                if binding.source_table_id == primary_id or context is primary_context
                else min(position, len(context["rows"]) - 1)
            )
            cells = _row_cells(
                context,
                position_for_table,
                refs_by_table.get(binding.source_table_id, ()),
            )
            if binding.formula:
                value = formulas.evaluate(binding.formula, cells)
            elif binding.source_column is not None:
                column_values = context["by_id"].get(
                    str(binding.source_column_id), []
                )
                value = (
                    column_values[position_for_table]
                    if position_for_table < len(column_values)
                    else None
                )
            else:
                value = next(iter(cells.values()), None)
            values[field_key] = value
        natural_key = _natural_key(link, values, row_index)
        items.append((natural_key, values))
    return items


def _column_letter(position):
    letters = ""
    position += 1
    while position:
        position, remainder = divmod(position - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _table_context(table):
    """Build positional/named accessors for a table's rows (Excel refs -> values)."""
    columns = sorted(table.columns.all(), key=lambda c: (c.slot, c.pk))
    rows = list(ExtractedTableRow.objects.filter(table=table).order_by("row_index"))
    by_letter = {}
    by_name = {}
    for index, column in enumerate(columns):
        letter = _column_letter(index)
        values = [(row.cells or {}).get(column.column_id) for row in rows]
        by_letter[letter] = values
        by_name[column.column_id] = values
        if column.label:
            by_name.setdefault(column.label, values)
    return {
        "rows": [row.row_index for row in rows],
        "letters": by_letter,
        "by_id": {str(column.pk): by_letter[_column_letter(i)] for i, column in enumerate(columns)},
        "by_name": by_name,
        "column_names": [column.column_id for column in columns],
    }


def _value_at(series, position):
    if series is None or position >= len(series):
        return None
    return series[position]


def _row_cells(context, position, references):
    """Build the ``{reference: value}`` map a formula is evaluated against for one row."""
    cells = {}
    for name, series in context["by_name"].items():
        cells[name] = _value_at(series, position)

    for reference in references:
        key = str(reference)
        if ":" in key:
            left = key.split(":", 1)[0].strip().lstrip("$")
            letter = re.sub(r"[^A-Za-z]", "", left).upper()
            series = context["letters"].get(letter)
            cells[key] = list(series) if series else None
        else:
            body = key.lstrip("$")
            match = re.match(r"^([A-Za-z]+)(\d+)$", body)
            if match:
                letter = match.group(1).upper()
                excel_row = int(match.group(2))
                cells[key] = _value_at(context["letters"].get(letter), excel_row - 2)
    return cells


def _natural_key(link, values, row_index):
    label = values.get("plan_name") or values.get("name") or ""
    label = str(label).strip()
    if label:
        return f"{link.pk}:{label}"[:512]
    return f"{link.pk}:row-{row_index}"[:512]


def clean_link_data(link, actor=None):
    """Run every mapped row through the cleaning engine (FR-032, FR-033, R12)."""
    from admin_console import cleaning

    recipe = get_current_recipe(link)
    if recipe is None or not recipe.is_complete:
        raise ApiError(
            "recipe_incomplete",
            "A complete recipe is required before cleaning.",
            http_status=409,
        )

    records = []
    exception_count = 0
    for natural_key, values in _recipe_row_values(link, recipe):
        cleaned, exceptions = cleaning.clean_record(recipe.plan_type, values)
        exception_count += len(exceptions)
        records.append(
            {
                "natural_key": natural_key,
                "plan_type": recipe.plan_type,
                "values": cleaned,
                "exceptions": exceptions,
            }
        )

    link.pipeline_stage = Link.PipelineStage.CLEANED
    link.save(update_fields=["pipeline_stage", "updated_at"])
    events.cleaning_completed(link, len(records), exception_count)
    return {
        "link_id": link.pk,
        "plan_type": recipe.plan_type,
        "recipe_id": recipe.pk,
        "cleaned_records": len(records),
        "exception_count": exception_count,
        "records": records,
    }


@transaction.atomic
def publish_link_data(link, actor=None):
    """Publish cleaned rows through ``CatalogInterface`` with full provenance (FR-034..FR-036)."""
    from admin_console import cleaning
    from catalog.interfaces import CatalogInterface

    recipe = get_current_recipe(link)
    if recipe is None or not recipe.is_complete:
        raise ApiError(
            "recipe_incomplete",
            "A complete recipe is required before publishing.",
            http_status=409,
        )
    if link.current_trace is None:
        raise ApiError(
            "trace_required",
            "A stored trace is required before publishing.",
            http_status=409,
        )

    published = 0
    exception_count = 0
    for natural_key, values in _recipe_row_values(link, recipe):
        cleaned, exceptions = cleaning.clean_record(recipe.plan_type, values)
        exception_count += len(exceptions)
        CatalogInterface.upsert_published_record(
            source="admin_console",
            site=link.site_id,
            link=link.pk,
            trace=link.current_trace_id,
            recipe=recipe.pk,
            plan_type=recipe.plan_type,
            natural_key=natural_key,
            values=cleaned,
            cleaning_exceptions=exceptions,
        )
        published += 1

    link.pipeline_stage = Link.PipelineStage.PUBLISHED
    link.save(update_fields=["pipeline_stage", "updated_at"])
    events.published(link, published)
    return {
        "link_id": link.pk,
        "published": published,
        "exception_count": exception_count,
        "pipeline_stage": link.pipeline_stage,
    }


# ---------------------------------------------------------------------------
# US8 — failure alerting and stage re-run (FR-040..FR-042)
# ---------------------------------------------------------------------------


def evaluate_failure_alert(link):
    """Transition the link's failure-alert state (state-based, FR-040, FR-041).

    Raises exactly one alert per crossing: while an alert is open, a still-high rate does
    not create another; a rate that falls back below the threshold resolves the open alert,
    so a later re-crossing opens a fresh one.
    """
    from notifications.interfaces import NotificationsInterface

    threshold = constants.failure_rate_threshold()
    open_alert = FailureAlert.objects.filter(
        link=link, state=FailureAlert.State.OPEN
    ).first()

    if link.failure_rate >= threshold:
        if open_alert is not None:
            open_alert.failure_rate = link.failure_rate
            open_alert.save(update_fields=["failure_rate", "updated_at"])
            return open_alert
        alert = FailureAlert.objects.create(
            link=link,
            state=FailureAlert.State.OPEN,
            failure_rate=link.failure_rate,
            raised_at=timezone.now(),
        )
        dedup_key = f"link_failure_rate_exceeded:{link.pk}:{alert.pk}"
        alert.notification_dedup_key = dedup_key
        alert.save(update_fields=["notification_dedup_key", "updated_at"])
        NotificationsInterface.notify(
            event_type="link_failure_rate_exceeded",
            subject=f"Link needs updating: {link.url}",
            body=(
                f"The failure rate for {link.url} reached "
                f"{link.failure_rate:.2f} (threshold {threshold:.2f})."
            ),
            severity=NotificationsInterface.Severity.WARNING,
            related_object=f"admin_console.Link:{link.pk}",
            dedup_key=dedup_key,
        )
        events.alert_raised(link, link.failure_rate)
        return alert

    if open_alert is not None:
        open_alert.state = FailureAlert.State.RESOLVED
        open_alert.resolved_at = timezone.now()
        open_alert.save(update_fields=["state", "resolved_at", "updated_at"])
        NotificationsInterface.resolve_notifications(
            event_type="link_failure_rate_exceeded",
            related_object=f"admin_console.Link:{link.pk}",
        )
        events.alert_resolved(link)
        return open_alert
    return None


def rerun_link_stages(link, actor=None):
    """Reset a flagged link to ``capture`` so all stages can be re-run (FR-042, SC-014)."""
    previous = link.pipeline_stage
    link.pipeline_stage = Link.PipelineStage.CAPTURE
    link.review_state = Link.ReviewState.KEPT
    link.is_active = True
    link.save(update_fields=["pipeline_stage", "review_state", "is_active", "updated_at"])
    open_alerts = FailureAlert.objects.filter(link=link, state=FailureAlert.State.OPEN)
    open_alerts.update(
        state=FailureAlert.State.RESOLVED,
        resolved_at=timezone.now(),
        updated_at=timezone.now(),
    )
    from notifications.interfaces import NotificationsInterface

    NotificationsInterface.resolve_notifications(
        event_type="link_failure_rate_exceeded",
        related_object=f"admin_console.Link:{link.pk}",
    )
    events.alert_resolved(link)
    return {
        "link_id": link.pk,
        "previous_stage": previous,
        "pipeline_stage": link.pipeline_stage,
    }


def replay_run_payload(run):
    return {
        "id": run.pk,
        "link_id": run.link_id,
        "recipe_id": run.recipe_id,
        "scheduled_for": run.scheduled_for.isoformat() if run.scheduled_for else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "state": run.state,
        "before_trace_id": run.before_trace_id,
        "after_trace_id": run.after_trace_id,
        "diff_summary": run.diff_summary,
        "diff_applied": run.diff_applied,
        "stats_applied": run.stats_applied,
        "stats_skipped": run.stats_skipped,
        "stats_failed": run.stats_failed,
        "failures": run.failures,
    }


def alert_payload(alert):
    return {
        "id": alert.pk,
        "link_id": alert.link_id,
        "state": alert.state,
        "failure_rate": alert.failure_rate,
        "raised_at": alert.raised_at.isoformat() if alert.raised_at else None,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        "notification_dedup_key": alert.notification_dedup_key,
    }


def due_links(now=None):
    """Links due for replay: active site, complete recipe, past the period (FR-037)."""
    now = now or timezone.now()
    period = timedelta(hours=constants.replay_period_hours())
    candidates = (
        Link.objects.filter(
            is_active=True,
            review_state=Link.ReviewState.KEPT,
            site__maintenance_state=Site.MaintenanceState.ACTIVE,
        )
        .select_related("site", "current_trace")
    )
    due = []
    for link in candidates:
        recipe = get_current_recipe(link)
        if recipe is None or not recipe.is_complete:
            continue
        if link.current_trace is None:
            continue
        if link.last_replay_at is not None and (now - link.last_replay_at) < period:
            continue
        due.append(link)
    return due[: constants.replay_batch_size()]


def due_links_for_site(site_id, now=None):
    """Due-to-replay links for one site (used by an on-demand replay request)."""
    return [link for link in due_links(now=now) if link.site_id == int(site_id)]


def replay_runs(link_id=None, limit=100):
    queryset = ReplayRun.objects.select_related("link").all()
    if link_id is not None:
        queryset = queryset.filter(link_id=link_id)
    return list(queryset[:limit])


def alerts(state=None, limit=200):
    queryset = FailureAlert.objects.select_related("link").all()
    if state:
        queryset = queryset.filter(state=state)
    return list(queryset[:limit])


def link_failure_payload(link):
    open_alert = FailureAlert.objects.filter(
        link=link, state=FailureAlert.State.OPEN
    ).first()
    window = max(1, constants.failure_rate_window_runs())
    recent = list(ReplayRun.objects.filter(link=link).order_by("-created_at")[:window])
    return {
        "link_id": link.pk,
        "pipeline_stage": link.pipeline_stage,
        "failure_rate": link.failure_rate,
        "threshold": constants.failure_rate_threshold(),
        "window_runs": window,
        "last_replay_at": link.last_replay_at.isoformat() if link.last_replay_at else None,
        "open_alert": alert_payload(open_alert) if open_alert else None,
        "recent_runs": [replay_run_payload(run) for run in recent],
    }


def metrics_snapshot():
    """Aggregate operational metrics for the console dashboard (FR-045, Principle VII)."""
    from django.db.models import Avg, Count, Q, Sum

    sites = Site.objects.all()
    crawl = sites.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(maintenance_state=Site.MaintenanceState.ACTIVE)),
        suspended=Count("id", filter=Q(maintenance_state=Site.MaintenanceState.SUSPENDED)),
    )
    links = Link.objects.aggregate(
        total=Count("id"),
        kept=Count("id", filter=Q(review_state=Link.ReviewState.KEPT)),
        flagged=Count("id", filter=Q(pipeline_stage=Link.PipelineStage.FLAGGED)),
        published=Count("id", filter=Q(pipeline_stage=Link.PipelineStage.PUBLISHED)),
        avg_failure_rate=Avg("failure_rate"),
    )
    total_sites = crawl["total"] or 0
    crawl_success_rate = (crawl["active"] / total_sites) if total_sites else 0.0

    runs = ReplayRun.objects.aggregate(
        applied=Sum("stats_applied"),
        failed=Sum("stats_failed"),
    )
    last_replay = ReplayRun.objects.order_by("-finished_at").first()
    staleness_seconds = None
    if last_replay and last_replay.finished_at:
        staleness_seconds = (timezone.now() - last_replay.finished_at).total_seconds()

    spend = LlmCostLedger.objects.filter(amount__isnull=False).aggregate(
        total=Sum("amount"), calls=Count("id")
    )
    return {
        "crawl": {
            "sites_total": total_sites,
            "sites_active": crawl["active"] or 0,
            "sites_suspended": crawl["suspended"] or 0,
            "success_rate": crawl_success_rate,
            "links_total": links["total"] or 0,
            "links_kept": links["kept"] or 0,
            "links_flagged": links["flagged"] or 0,
            "links_published": links["published"] or 0,
            "avg_failure_rate": links["avg_failure_rate"] or 0.0,
        },
        "replay": {
            "applied": runs["applied"] or 0,
            "failed": runs["failed"] or 0,
            "staleness_seconds": staleness_seconds,
            "open_alerts": FailureAlert.objects.filter(
                state=FailureAlert.State.OPEN
            ).count(),
        },
        "llm": {
            "call_count": spend["calls"] or 0,
            "total_cost": float(spend["total"] or 0),
            "labeling_enabled": constants.labeling_enabled(),
        },
    }
