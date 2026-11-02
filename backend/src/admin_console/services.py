"""The automated site-maintenance pipeline (spec 003).

Every stage is server-side and per-link isolated: discovery → headless capture →
table extraction → table labeling → plan data → publish, with compare-driven replay on
top. crawl4ai's adaptive crawler (statistical strategy) owns link relevance, so
discovery feeds capture directly. LLM-gated stages are gated by the admin-owned token
budget; when it is exhausted the link parks in ``awaiting_llm_budget`` and resumes
later (FR-047..FR-050). Network/provider failures are retried with backoff and
dead-lettered on exhaustion (FR-051, FR-052).
"""

import hashlib
import math
import re
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
from admin_console.models import (
    CaptureSession,
    ChangeRecord,
    ExtractedTable,
    ExtractedTableColumn,
    ExtractedTableRow,
    FailureAlert,
    Link,
    PlanExclusion,
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
    if outcome == "approved":
        from admin_console.tasks import run_site_pipeline_task

        transaction.on_commit(lambda: run_site_pipeline_task.enqueue(site.pk))
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
                "review_state": Link.ReviewState.KEPT,
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
        harvested.extend(
            discovery.crawl_candidate_links(site.domain, query, bounds=bounds)
        )
    reduced = discovery.apply_link_policy(harvested, host=host)
    stored = _store_links(site, reduced, Link.Source.ADAPTIVE_CRAWL)
    site.last_discovered_at = timezone.now()
    site.save(update_fields=["last_discovered_at", "updated_at"])
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
# US4 — server-side headless capture (FR-016..FR-019)
# ---------------------------------------------------------------------------


def _materialize(trace):
    return artifacts.materialize(trace.storage_key, backend=trace.storage_backend)


def start_capture(link, actor=None, duration_ms=None):
    """Create a headless capture session and record the trace (FR-016..FR-019)."""
    if link.review_state != Link.ReviewState.KEPT:
        raise ValueError("link_not_ready")
    if link.capture_sessions.filter(state__in=CaptureSession.NON_TERMINAL).exists():
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
        path,
        min_rows=config["min_rows"],
        min_cols=config["min_cols"],
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
        ExtractedTableRow.objects.create(table=record, row_index=row_index, cells=row)
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
    """A compact table view for the LLM: column labels + rows (no selectors needed).

    When pass 1 (``domtrack tables label``) has run, its table ``title``/``purpose`` and
    each column's ``semantic_label`` are attached so pass 2 extracts against the schema
    using the semantic hints.
    """
    columns = list(table.columns.all())
    semantic = {
        label.column_id: label.label
        for label in table.semantic_labels.select_related("column").all()
        if label.column_id and label.label
    }
    return {
        "columns": [
            semantic.get(column.pk) or column.label or column.column_id
            for column in columns
        ],
        "rows": [
            [row.cells.get(column.column_id, "") for column in columns]
            for row in table.rows.all()
        ],
    }


# ---------------------------------------------------------------------------
# US6/US7 — classification, labeling, then schema extraction
# (FR-023..FR-031)
# ---------------------------------------------------------------------------


def classify_link_tables(link, actor=None):
    """Classify each table before labeling; extract only accepted tables."""
    tables = list(link.extracted_tables.all())
    if not tables:
        raise ValueError("no_tables_found")
    existing = {
        item.table_id: item
        for item in TableClassification.objects.filter(table__link=link)
    }
    for index, table in enumerate(tables):
        if table.pk in existing:
            continue
        verdict = llm.classify_tables(
            [{"table_index": index, **_table_context(table)}],
            link=link,
            idempotency_key=f"classification:{link.pk}:{table.pk}",
        )[0]
        classification = TableClassification.objects.create(
            table=table,
            is_plans_table=verdict.is_correct,
            plan_type=verdict.plan_type or "",
            confidence=verdict.classification_confidence or 0.0,
            provider=constants.labeling_provider(),
            model=constants.labeling_model() or "",
            prompt_version=llm.PROMPT_VERSION,
        )
        existing[table.pk] = classification
    accepted = [table for table in tables if existing[table.pk].is_plans_table]
    if not accepted:
        link.pipeline_stage = Link.PipelineStage.NO_PLANS
        link.save()
        events.classification_completed(link, 0, len(tables))
        events.no_plans_found(link, len(tables))
        return link
    label_link_tables(link, tables=accepted)
    plans_count = 0
    skipped = 0
    pending_records = []
    with transaction.atomic():
        PlanRecord.objects.filter(link=link).delete()
        for table in accepted:
            classification = existing[table.pk]
            plan_type = classification.plan_type
            plans = llm.extract_plans(
                _table_context(table),
                plan_type,
                {field.key for field in plan_schema.schema_for(plan_type).fields},
                link=link,
                table=table,
                idempotency_key=f"schema-extraction:{link.pk}:{table.pk}",
            )
            plans_count += 1
            for plan in plans:
                confidence = 1.0 if plan.confidence is None else plan.confidence
                values = _normalize_price_scale(plan.values, _table_context(table))
                if not _plan_is_complete(values, plan_type, confidence):
                    skipped += 1
                    continue
                pending_records.append(
                    PlanRecord(
                        link=link,
                        table=table,
                        classification=classification,
                        plan_type=plan_type,
                        natural_key=_natural_key(
                            values, plan_type, len(pending_records)
                        ),
                        values=values,
                        confidence=confidence,
                        prompt_version=llm.PROMPT_VERSION,
                    )
                )
        if pending_records:
            PlanRecord.objects.bulk_create(pending_records)
    if pending_records:
        link.pipeline_stage = Link.PipelineStage.PLANS_EXTRACTED
    elif plans_count:
        link.pipeline_stage = Link.PipelineStage.EXTRACTED
    else:
        link.pipeline_stage = Link.PipelineStage.NO_PLANS
    link.save()
    events.classification_completed(link, plans_count, len(tables))
    if pending_records:
        events.plans_extracted(link, len(pending_records), skipped)
    elif plans_count:
        raise llm.NoPlanRecordsError(
            "no plan records met confidence and required-field rules; each needs a "
            "directly supported name, positive price, and confidence 1.0"
        )
    else:
        events.no_plans_found(link, len(tables))
    return link


# Kept as a compatibility entry point for existing callers while the pipeline
# now performs classification, labeling, and schema extraction as separate stages.
def classify_and_extract_link_tables(link, actor=None):
    return classify_link_tables(link, actor=actor)


_PRICE_SCALE_FACTORS = (
    (re.compile(r"(?:میلیون|million)", re.IGNORECASE), 1_000_000),
    (re.compile(r"(?:هزار|thousand)", re.IGNORECASE), 1_000),
    (re.compile(r"(?:میلیارد|billion)", re.IGNORECASE), 1_000_000_000),
)
_LOCALIZED_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _numeric_cell(value):
    text = str(value).translate(_LOCALIZED_DIGITS).strip()
    text = text.replace(",", "").replace("٬", "")
    if not re.fullmatch(r"\d+(?:\.\d+)?", text):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_price_scale(values, table_context):
    """Normalize a model price using the closest explicit unit in its source row.

    The combined LLM prompt requests normalized toman values. This source check is a
    guard against providers returning the displayed number without applying its scale.
    """
    result = dict(values)
    price = _numeric_cell(result.get("price_amount"))
    plan_name = " ".join(str(result.get("plan_name") or "").split()).casefold()
    if price is None or not plan_name:
        return result

    for row in table_context.get("rows", []):
        row_text = [" ".join(str(cell).split()) for cell in row]
        if not any(plan_name == cell.casefold() for cell in row_text):
            continue
        for cell_index, cell in enumerate(row_text):
            source_amount = _numeric_cell(cell)
            if source_amount is None or source_amount <= 0:
                continue
            ratio = price / source_amount
            recognized_scales = (1, 1_000, 1_000_000, 1_000_000_000)
            if not any(
                math.isclose(ratio, scale, rel_tol=1e-9) for scale in recognized_scales
            ):
                continue
            for unit_cell in reversed(row_text[:cell_index]):
                unit = unit_cell.casefold()
                factor = next(
                    (
                        scale
                        for pattern, scale in _PRICE_SCALE_FACTORS
                        if pattern.search(unit)
                    ),
                    None,
                )
                if factor is not None:
                    normalized = source_amount * factor
                    result["price_amount"] = (
                        int(normalized) if normalized.is_integer() else normalized
                    )
                    return result
    return result


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
    """Schema-extract plan data from tables pass 2 already classified as plans.

    The pipeline's primary path is the single combined pass
    (:func:`classify_and_extract_link_tables`); this remains for re-extraction against
    the schema without repeating classification.
    """
    tables = [
        table
        for table in link.extracted_tables.all()
        if getattr(table, "classification", None) is not None
        and table.classification.is_plans_table
        and table.classification.plan_type in plan_schema.PLAN_SCHEMA
    ]
    if not tables:
        raise ValueError("plans_required")
    skipped = 0
    pending_records = []
    for table in tables:
        classification = table.classification
        plan_type = classification.plan_type
        plans = llm.extract_plans(
            _table_context(table),
            plan_type,
            plan_schema.all_field_keys(plan_type),
            link=link,
            table=table,
            idempotency_key=f"plans:{table.pk}",
        )
        valid = [
            plan
            for plan in plans
            if _plan_is_complete(plan.values, plan_type, plan.confidence)
        ]
        skipped += len(plans) - len(valid)
        if not valid:
            if not plans:
                skipped += 1
            continue
        for plan in valid:
            pending_records.append(
                PlanRecord(
                    link=link,
                    table=table,
                    classification=classification,
                    plan_type=plan_type,
                    natural_key=_natural_key(
                        plan.values, plan_type, len(pending_records)
                    ),
                    values=plan.values,
                    confidence=plan.confidence,
                    prompt_version=llm.PROMPT_VERSION,
                )
            )
    if not pending_records:
        raise llm.NoPlanRecordsError(
            "no plan records met confidence and required-field rules; each needs a "
            "directly supported name, positive price, and confidence 1.0"
        )
    with transaction.atomic():
        PlanRecord.objects.filter(link=link).delete()
        PlanRecord.objects.bulk_create(pending_records)
    link.pipeline_stage = Link.PipelineStage.PLANS_EXTRACTED
    link.save()
    events.plans_extracted(link, len(pending_records), skipped)
    return link


def _plan_is_complete(values, plan_type, confidence):
    if confidence != 1.0:
        return False
    required = plan_schema.required_keys(plan_type)
    if not all(values.get(key) not in (None, "") for key in required):
        return False
    name = values.get("plan_name")
    price = values.get("price_amount")
    return (
        isinstance(name, str)
        and bool(name.strip())
        and isinstance(price, (int, float))
        and not isinstance(price, bool)
        and math.isfinite(price)
        and price > 0
    )


def _natural_key(values, plan_type, index):
    name = values.get("plan_name") or f"{plan_type}-{index}"
    return f"{plan_type}:{name}:{index}"


def plans_payload(link):
    excluded = set(link.plan_exclusions.values_list("fingerprint", flat=True))
    return [
        {
            "id": plan.pk,
            "classification_id": plan.classification_id,
            "trace_id": plan.table.trace_id,
            "plan_type": plan.plan_type,
            "natural_key": plan.natural_key,
            "values": plan.values,
            "confidence": plan.confidence,
            "ignored": plan_fingerprint(plan.plan_type, plan.values) in excluded,
        }
        for plan in link.plan_records.select_related("table").all()
    ]


def plan_fingerprint(plan_type, values):
    name = " ".join(str(values.get("plan_name", "")).split()).casefold()
    identity = f"{plan_type}\x1f{name}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def set_plan_excluded(link, plan, ignored):
    fingerprint = plan_fingerprint(plan.plan_type, plan.values)
    exclusion = PlanExclusion.objects.filter(link=link, fingerprint=fingerprint)
    if ignored:
        PlanExclusion.objects.get_or_create(
            link=link,
            fingerprint=fingerprint,
            defaults={
                "plan_type": plan.plan_type,
                "plan_name": str(plan.values.get("plan_name", ""))[:255],
                "price_amount": str(plan.values.get("price_amount", ""))[:64],
            },
        )
        from catalog.interfaces import CatalogInterface

        CatalogInterface.retire_published_record(
            site=link.site_id, natural_key=plan.natural_key
        )
    else:
        exclusion.delete()
    return ignored


def unignored_plan_keys(link):
    excluded = set(link.plan_exclusions.values_list("fingerprint", flat=True))
    return {
        plan.natural_key
        for plan in link.plan_records.all()
        if plan_fingerprint(plan.plan_type, plan.values) not in excluded
    }


# ---------------------------------------------------------------------------
# US8 — mandatory LLM table labeling, pass 1 (FR-032..FR-035)
# ---------------------------------------------------------------------------


def label_link_tables(link, actor=None, tables=None):
    """Label every extracted table with ``domtrack tables label`` (pass 1).

    The result feeds pass 2 (:func:`classify_and_extract_link_tables`) as semantic
    column hints. domtrack returns the same table shape it was given with ``meta.title``,
    ``meta.purpose`` and per-column ``semantic_label`` merged in, so the discovered
    tables are passed through verbatim rather than rebuilt from our columns.
    """
    tables = list(tables if tables is not None else link.extracted_tables.all())
    if not tables:
        raise ValueError("no_tables_found")
    # domtrack's labeler calls the provider directly, so the admin token budget has to
    # be enforced here before any spend happens (FR-048).
    llm.default_budget.guard("labeling", link=link)
    config = constants.labeling_config()
    labels = []
    provider = config["provider"]
    model = config["model"] or ""
    language = config["language"]
    with transaction.atomic():
        SemanticLabel.objects.filter(table__link=link).delete()
        for table in tables:
            llm.default_budget.guard("labeling", link=link)
            result = domtrack_client.label_tables([_domtrack_table(table)], config)
            entry = ((result or {}).get("tables") or [{}])[0]
            for column_index, column in enumerate(table.columns.all()):
                label = _column_label(entry, column_index)
                if not label:
                    continue
                SemanticLabel.objects.create(
                    table=table,
                    column=column,
                    label=label,
                    provider=provider,
                    model=model,
                    language=language,
                )
                labels.append(
                    {
                        "table_id": table.pk,
                        "column_id": column.column_id,
                        "label": label,
                    }
                )
    events.labeling_run(link, len(tables), 0)
    return labels


def _domtrack_table(table):
    """Rebuild the domtrack table record stored at extraction time (FR-020).

    ``domtrack tables label`` expects the discovery output shape (``parent``/``meta``/
    ``columns``/``rows``). Rows are reconstructed from the persisted cells.
    """
    columns = list(table.columns.all())
    return {
        "parent": {"id": 0, "tag": table.parent, "classes": []},
        "meta": {
            "parent_tag": table.parent,
            "parent_classes": [],
            "row_count": table.row_count,
            **{
                key: value
                for key, value in (table.meta or {}).items()
                if key not in ("parent_tag", "parent_classes", "row_count")
            },
        },
        "columns": [
            {
                "id": column.column_id,
                "label": column.label,
                "path": column.path,
                "atype": column.atype,
                "slot": column.slot,
                "coverage": column.coverage,
                "row_count": column.row_count,
            }
            for column in columns
        ],
        "rows": [
            {
                column.column_id: row.cells.get(column.column_id, "")
                for column in columns
            }
            for row in table.rows.all()
        ],
        "row_count": table.row_count,
        "column_count": table.column_count,
        "score": table.score,
    }


def _column_label(entry, column_index):
    """Read the merged ``semantic_label`` for a table's ``column_index``-th column."""
    columns = entry.get("columns") or []
    if column_index >= len(columns):
        return ""
    candidate = columns[column_index]
    if not isinstance(candidate, dict):
        return ""
    return candidate.get("semantic_label") or ""
    return ""


# ---------------------------------------------------------------------------
# US9 — publishing (FR-036..FR-038)
# ---------------------------------------------------------------------------


def publish_link_plans(link, actor=None):
    from catalog.interfaces import CatalogInterface

    plans = list(link.plan_records.all())
    if not plans:
        raise ValueError("plans_required")
    excluded = set(link.plan_exclusions.values_list("fingerprint", flat=True))
    published = 0
    for plan in plans:
        if (
            not _plan_is_complete(plan.values, plan.plan_type, plan.confidence)
            or plan_fingerprint(plan.plan_type, plan.values) in excluded
        ):
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
    if not published and not all(
        plan_fingerprint(plan.plan_type, plan.values) in excluded for plan in plans
    ):
        raise ValueError("no_plan_records_met_quality_rules")
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
    if link.pipeline_stage == Link.PipelineStage.DEAD_LETTERED:
        link.pipeline_stage = (
            Link.PipelineStage.CAPTURED
            if link.current_trace_id
            else Link.PipelineStage.DISCOVERED
        )
    elif link.pipeline_stage == Link.PipelineStage.NO_PLANS:
        # The tables were already extracted; re-run labeling + classification on the
        # stored tables rather than a fresh capture.
        link.pipeline_stage = Link.PipelineStage.EXTRACTED
    elif link.pipeline_stage == Link.PipelineStage.AWAITING_LLM_BUDGET:
        awaiting_stage = link.last_error.rsplit(":", 1)[-1]
        link.pipeline_stage = {
            "labeling": Link.PipelineStage.EXTRACTED,
            "classification": Link.PipelineStage.EXTRACTED,
            "schema_extraction": Link.PipelineStage.EXTRACTED,
        }.get(awaiting_stage, Link.PipelineStage.DISCOVERED)
    link.last_error = ""
    link.retry_count = 0
    link.save(
        update_fields=["pipeline_stage", "retry_count", "last_error", "updated_at"]
    )
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
        .filter(models_q_last_replay(cutoff))
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
