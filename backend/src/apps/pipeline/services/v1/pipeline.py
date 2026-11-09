"""The automated site-maintenance pipeline (spec 003).

Every stage is server-side and per-link isolated: discovery → headless capture →
table extraction → table labeling → plan data → publish, with compare-driven replay on
top. crawl4ai's adaptive crawler (statistical strategy) owns link relevance, so
discovery feeds capture directly. LLM-gated stages are gated by the admin-owned token
budget; when it is exhausted the link parks in ``awaiting_llm_budget`` and resumes
later (FR-047..FR-050). Network/provider failures are retried with backoff and
dead-lettered on exhaustion (FR-051, FR-052); other failures are recorded once and
re-raised without retries.
"""

import hashlib
import json
import math
import re
import time
import urllib.parse
from collections import Counter
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q
from django.utils import timezone

from apps.pipeline import (
    artifacts,
    constants,
    discovery,
    domtrack_client,
    events,
    llm,
    plan_schema,
)
from apps.pipeline.models import (
    CaptureSession,
    ExtractedTable,
    ExtractedTableColumn,
    ExtractedTableRow,
    FailureAlert,
    Link,
    PlanExclusion,
    PlanRecord,
    TableClassification,
    ReplayRun,
    SemanticLabel,
    Site,
    Trace,
)
from apps.pipeline.table_classifier import TableClassifier

#: Failures worth retrying with backoff. ``llm.RETRYABLE_ERRORS`` (optional tuple of
#: provider exception classes) extends the set; everything else fails fast.
_REMOTE_ERRORS = (domtrack_client.DomtrackCaptureError, OSError, TimeoutError)


def _retryable_errors():
    return _REMOTE_ERRORS + tuple(getattr(llm, "RETRYABLE_ERRORS", ()))


class CaptureInProgress(RuntimeError):
    """A non-terminal capture session already exists for the link."""

    def __init__(self, message="capture_in_progress"):
        super().__init__(message)


def _sleep(seconds):
    time.sleep(seconds)


# ---------------------------------------------------------------------------
# US2 — automated link discovery (FR-007..FR-011)
# ---------------------------------------------------------------------------


def _url_hash(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def onboard_site(company_id, actor=None):
    from apps.companies.models import Company

    company = Company.objects.get(pk=company_id)
    site, created = Site.objects.get_or_create(
        company=company,
        defaults={
            "domain": company.domain,
            "maintenance_state": Site.MaintenanceState.ONBOARDING,
            "onboarded_at": timezone.now(),
        },
    )
    if created:
        events.site_onboarded(site, actor=actor)
    return site


def _store_links(site, urls, source):
    """Insert links not seen before; two queries instead of one per URL."""
    by_hash = {}
    for url in urls:
        by_hash.setdefault(_url_hash(url), url)
    if not by_hash:
        return []
    existing = set(
        Link.objects.filter(site=site, url_hash__in=by_hash).values_list(
            "url_hash", flat=True
        )
    )
    new_hashes = [h for h in by_hash if h not in existing]
    if not new_hashes:
        return []
    Link.objects.bulk_create(
        [
            Link(
                site=site,
                url=by_hash[h],
                url_hash=h,
                source=source,
                review_state=Link.ReviewState.KEPT,
                pipeline_stage=Link.PipelineStage.DISCOVERED,
            )
            for h in new_hashes
        ],
        ignore_conflicts=True,
    )
    # ignore_conflicts leaves pks unset, so reload what actually exists.
    return list(Link.objects.filter(site=site, url_hash__in=new_hashes))


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
    if not reduced:
        # Only "the crawl found nothing" is an alert; re-finding known links is not.
        _notify_empty_discovery(site)
    return {"discovered": len(harvested), "after_policy": len(reduced), "links": stored}


def _notify_empty_discovery(site):
    """Tell the operator a crawl found nothing so the site stays visible (FR-011)."""
    events.empty_discovery(site)


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


def _is_valid_trace_bytes(data):
    try:
        raw = json.loads(data)
    except (ValueError, TypeError):
        return False
    return isinstance(raw, dict) and domtrack_client.is_trace(raw)


def start_capture(link, actor=None, duration_ms=None):
    """Create a headless capture session and record the trace (FR-016..FR-019)."""
    if link.review_state != Link.ReviewState.KEPT:
        raise ValueError("link_not_ready")
    if link.capture_sessions.filter(state__in=CaptureSession.NON_TERMINAL).exists():
        raise CaptureInProgress()
    duration = int(duration_ms or constants.capture_fixed_duration_ms())
    try:
        # Savepoint, so losing the unique-constraint race doesn't poison an outer
        # transaction.
        with transaction.atomic():
            session = CaptureSession.objects.create(
                link=link,
                mode=CaptureSession.Mode.HEADLESS_FIXED,
                state=CaptureSession.State.RECORDING,
                duration_ms=duration,
            )
    except IntegrityError as exc:
        raise CaptureInProgress() from exc
    events.capture_started(link, session)

    def _run():
        return domtrack_client.capture_headless(
            link.url, duration, constants.capture_nav_timeout_ms()
        )

    try:
        data = _run_with_retries("capture", link, _run)
        if not _is_valid_trace_bytes(data):
            raise ValueError("invalid_trace")
        key, backend, size, digest = artifacts.save_trace(data)
        with transaction.atomic():
            trace = Trace.objects.create(
                link=link,
                capture_session=session,
                captured_at=timezone.now(),
                origin=Trace.Origin.SERVER_CAPTURE,
                storage_key=key,
                storage_backend=backend,
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
            link.save(
                update_fields=[
                    "current_trace",
                    "pipeline_stage",
                    "retry_count",
                    "last_error",
                    "updated_at",
                ]
            )
    except Exception as exc:  # noqa: BLE001 - the failed attempt must be recorded
        # Any failure after the session exists must close it, otherwise it stays
        # ``recording`` and blocks every later capture of this link.
        fail_capture(session, exc)
        events.capture_failed(link, session, str(exc)[:200])
        raise
    events.trace_stored(trace, digest)
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
    result = _run_with_retries(
        "extraction",
        link,
        domtrack_client.extract_tables,
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
    link.save(update_fields=["pipeline_stage", "updated_at"])
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
    ExtractedTableColumn.objects.bulk_create(
        [
            ExtractedTableColumn(
                table=record,
                column_id=column["id"],
                label=column.get("label") or "",
                path=column.get("path") or "",
                atype=column.get("atype") or "",
                slot="" if column.get("slot") is None else str(column.get("slot")),
                coverage=float(column.get("coverage") or 0.0),
                row_count=int(column.get("row_count") or 0),
            )
            for column in columns
        ]
    )
    ExtractedTableRow.objects.bulk_create(
        [
            ExtractedTableRow(table=record, row_index=row_index, cells=row)
            for row_index, row in enumerate(rows)
        ],
        batch_size=500,
    )
    return record


def tables_payload(link):
    tables = []
    queryset = link.extracted_tables.select_related("classification").prefetch_related(
        "columns", "rows"
    )
    for table in queryset:
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
                        "is_price_table": classification.is_price_table,
                    }
                    if classification
                    else None
                ),
            }
        )
    return tables


def _table_context(table):
    """A compact table view for the LLM: column labels + rows (no selectors needed).

    When pass 1 (``domtrack tables label``) has run, each column's ``semantic_label``
    is attached so pass 2 extracts against the schema using the semantic hints.
    Semantic labels are deliberately *not* prefetched by callers: they are created
    between pass 1 and pass 2 and a prefetch cache would be stale.
    """
    columns = list(table.columns.all())
    semantic = {
        label.column_id: label.label
        for label in table.semantic_labels.all()
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
# US6/US7 — rule-based table filtering, labeling, then schema extraction
# (FR-023..FR-031)
# ---------------------------------------------------------------------------


def classify_tables_for_link(link, actor=None):
    """Evaluate every extracted table and persist its price-table boolean."""
    tables = list(link.extracted_tables.prefetch_related("rows"))
    if not tables:
        raise ValueError("no_tables_found")
    classifier = TableClassifier()
    classifications = {}
    for table in tables:
        is_price_table, matching_rows = classifier.detect(table)
        classification, _ = TableClassification.objects.update_or_create(
            table=table,
            defaults={
                "is_price_table": is_price_table,
                "matching_rows": matching_rows,
            },
        )
        classifications[table.pk] = classification
    accepted = [table for table in tables if classifications[table.pk].is_price_table]
    if not accepted:
        link.pipeline_stage = Link.PipelineStage.NO_PRICE_TABLES
        link.save(update_fields=["pipeline_stage", "updated_at"])
        events.no_price_tables_found(link, len(tables))
    events.price_table_detection_completed(link, len(accepted), len(tables))
    return link


def _extract_plan_records(link, tables):
    """Run schema extraction over ``tables``; return ``(processed, skipped, records)``.

    The single implementation behind :func:`process_link_tables` and
    :func:`extract_link_plans`, so both normalise, validate and key plans identically.
    """
    skipped = 0
    processed = 0
    pending_records = []
    seen_plans = set()
    ordinals = Counter()
    for table in tables:
        classification = table.classification
        table_context = _table_context(table)
        plan_type, plans = _run_with_retries(
            "schema_extraction",
            link,
            llm.infer_and_extract_plans,
            table_context,
            link=link,
            table=table,
            idempotency_key=f"schema-extraction:{link.pk}:{table.pk}",
        )
        classification.plan_type = plan_type
        classification.confidence = 1.0
        classification.save(update_fields=["plan_type", "confidence", "updated_at"])
        processed += 1
        for plan in plans:
            confidence = 1.0 if plan.confidence is None else plan.confidence
            values = _normalize_price_scale(plan.values, table_context)
            if not _plan_is_complete(values, plan_type, confidence):
                skipped += 1
                continue
            identity = _plan_values_identity(plan_type, values)
            if identity in seen_plans:
                skipped += 1
                continue
            seen_plans.add(identity)
            pending_records.append(
                PlanRecord(
                    link=link,
                    table=table,
                    classification=classification,
                    plan_type=plan_type,
                    natural_key=_natural_key(values, plan_type, ordinals=ordinals),
                    values=values,
                    confidence=confidence,
                    prompt_version=llm.PROMPT_VERSION,
                )
            )
    return processed, skipped, pending_records


def _replace_plan_records(link, pending_records):
    with transaction.atomic():
        PlanRecord.objects.filter(link=link).delete()
        PlanRecord.objects.bulk_create(pending_records)


def process_link_tables(link, actor=None):
    """Classify tables, then label and extract data from accepted tables."""
    classify_tables_for_link(link, actor=actor)
    accepted = list(
        link.extracted_tables.filter(classification__is_price_table=True)
        .select_related("classification")
        .prefetch_related("columns", "rows")
    )
    if not accepted:
        return link
    label_link_tables(link, tables=accepted)
    processed, skipped, pending_records = _extract_plan_records(link, accepted)
    if pending_records:
        # Only replace existing plans when there is something to replace them with;
        # one bad LLM run must not wipe previously good data.
        _replace_plan_records(link, pending_records)
        link.pipeline_stage = Link.PipelineStage.PLANS_EXTRACTED
    else:
        link.pipeline_stage = Link.PipelineStage.EXTRACTED
    link.save(update_fields=["pipeline_stage", "updated_at"])
    if pending_records:
        events.plans_extracted(link, len(pending_records), skipped)
    elif processed:
        raise llm.NoPlanRecordsError(
            "no plan records met confidence and required-field rules; each needs a "
            "directly supported name, positive price, and confidence 1.0"
        )
    return link


_PRICE_SCALE_PATTERNS = (
    (re.compile(r"(?:میلیارد|billion)", re.IGNORECASE), Decimal(1_000_000_000)),
    (re.compile(r"(?:میلیون|million)", re.IGNORECASE), Decimal(1_000_000)),
    (re.compile(r"(?:هزار|thousand)", re.IGNORECASE), Decimal(1_000)),
)
_PRICE_SCALE_VALUES = (
    Decimal(1),
    Decimal(1_000),
    Decimal(1_000_000),
    Decimal(1_000_000_000),
)
_PRICE_SCALE_FACTORS = _PRICE_SCALE_PATTERNS  # backward-compatible alias
_LOCALIZED_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _normalize_digits(text):
    text = str(text).translate(_LOCALIZED_DIGITS)
    for separator in (",", "٬", "،"):
        text = text.replace(separator, "")
    return text.replace("٫", ".")


def _numeric_cell(value):
    text = _normalize_digits(value).strip()
    if not re.fullmatch(r"\d+(?:\.\d+)?", text):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _split_amount(text):
    """``'۱۲۰ هزار تومان'`` → ``(Decimal(120), 'هزار تومان')``; ``(None, '')`` if no number."""
    match = re.match(r"^(\d+(?:\.\d+)?)\s*(\D*)$", _normalize_digits(text).strip())
    if not match:
        return None, ""
    return Decimal(match.group(1)), match.group(2).strip()


def _scale_in(text):
    for pattern, factor in _PRICE_SCALE_PATTERNS:
        if pattern.search(text or ""):
            return factor
    return None


def _coerce_price(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            number = Decimal(str(value))
        except InvalidOperation:
            return None
    elif isinstance(value, str):
        number, unit = _split_amount(value)
        if number is None or unit:
            return None
    else:
        return None
    return number if number.is_finite() else None


def _as_number(value):
    return int(value) if value == value.to_integral_value() else float(value)


def _normalize_price_scale(values, table_context):
    """Normalize a model price using the explicit unit nearest its source cell.

    The combined LLM prompt requests normalized toman values. This source check is a
    guard against providers returning the displayed number without applying its scale.
    Units are read from the amount's own cell (``120 هزار تومان``), a short unit-only
    cell before it, or the column header. String prices such as ``"120,000"`` are
    coerced to numbers. All arithmetic uses :class:`~decimal.Decimal`.
    """
    result = dict(values)
    price = _coerce_price(result.get("price_amount"))
    if price is None:
        return result
    result["price_amount"] = _as_number(price)
    plan_name = " ".join(str(result.get("plan_name") or "").split()).casefold()
    if not plan_name or price <= 0:
        return result

    headers = table_context.get("columns", [])
    for row in table_context.get("rows", []):
        row_text = [" ".join(str(cell).split()) for cell in row]
        if not any(plan_name == cell.casefold() for cell in row_text):
            continue
        for index, cell in enumerate(row_text):
            amount, unit = _split_amount(cell)
            if amount is None or amount <= 0 or len(unit.split()) > 3:
                continue
            if (price / amount) not in _PRICE_SCALE_VALUES:
                continue
            factor = _scale_in(unit)
            if factor is None:
                for previous in reversed(row_text[:index]):
                    if len(previous.split()) <= 3 and not re.search(
                        r"\d", _normalize_digits(previous)
                    ):
                        factor = _scale_in(previous)
                        if factor is not None:
                            break
            if factor is None and index < len(headers):
                factor = _scale_in(str(headers[index]))
            if factor is None:
                continue
            if (price / amount) != factor:
                result["price_amount"] = _as_number(amount * factor)
            return result
    return result


def table_classifications_payload(link):
    results = []
    for table in link.extracted_tables.select_related("classification"):
        classification = getattr(table, "classification", None)
        if classification is None:
            continue
        results.append(
            {
                "table_id": table.pk,
                "is_price_table": classification.is_price_table,
            }
        )
    return results


# ---------------------------------------------------------------------------
# US7 — plan schema extraction (data, not formulas) (FR-026..FR-031)
# ---------------------------------------------------------------------------


def extract_link_plans(link, actor=None):
    """Schema-extract plan data from tables already classified as price tables.

    The pipeline's primary path is :func:`process_link_tables`; this re-runs schema
    extraction without repeating classification, using the same shared helper.
    """
    tables = list(
        link.extracted_tables.filter(classification__is_price_table=True)
        .select_related("classification")
        .prefetch_related("columns", "rows")
    )
    if not tables:
        raise ValueError("plans_required")
    _, skipped, pending_records = _extract_plan_records(link, tables)
    if not pending_records:
        raise llm.NoPlanRecordsError(
            "no plan records met confidence and required-field rules; each needs a "
            "directly supported name, positive price, and confidence 1.0"
        )
    _replace_plan_records(link, pending_records)
    link.pipeline_stage = Link.PipelineStage.PLANS_EXTRACTED
    link.save(update_fields=["pipeline_stage", "updated_at"])
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


def _natural_key(values, plan_type, index=None, ordinals=None):
    """Stable key: ``type:name:n`` where ``n`` counts same-named plans.

    The old positional index changed whenever the LLM reordered plans or a plan was
    skipped, which churned published records. Pass a shared ``Counter`` as
    ``ordinals``; ``index`` is kept only for backward-compatible direct calls.
    """
    name = " ".join(str(values.get("plan_name") or "").split()).casefold()
    if ordinals is None:
        return f"{plan_type}:{name or f'{plan_type}-{index}'}:{index}"
    name = name or plan_type
    ordinals[(plan_type, name)] += 1
    return f"{plan_type}:{name}:{ordinals[(plan_type, name)]}"


def _plan_values_identity(plan_type, values):
    """Identify exact duplicate extracted plans while preserving meaningful variants."""
    values = {
        key: value for key, value in (values or {}).items() if key != "other"
    }
    serialized = json.dumps(
        {"plan_type": plan_type, "values": values},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _without_other(values):
    """Drop the legacy ``other`` bucket from values written or read by the pipeline."""
    return {
        key: value for key, value in (values or {}).items() if key != "other"
    }


def plans_payload(link):
    excluded = set(link.plan_exclusions.values_list("fingerprint", flat=True))
    return [
        {
            "id": plan.pk,
            "classification_id": plan.classification_id,
            "trace_id": plan.table.trace_id,
            "plan_type": plan.plan_type,
            "natural_key": plan.natural_key,
            "values": _without_other(plan.values),
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
        from apps.catalog.interfaces import CatalogInterface

        # One transaction so the exclusion and the retirement can't diverge.
        with transaction.atomic():
            PlanExclusion.objects.get_or_create(
                link=link,
                fingerprint=fingerprint,
                defaults={
                    "plan_type": plan.plan_type,
                    "plan_name": str(plan.values.get("plan_name", ""))[:255],
                    "price_amount": str(plan.values.get("price_amount", ""))[:64],
                },
            )
            CatalogInterface.retire_published_record(
                source="admin_console",
                site=link.site_id,
                natural_key=plan.natural_key,
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

    The result feeds pass 2 (:func:`process_link_tables`) as semantic
    column hints. domtrack returns the same table shape it was given with ``meta.title``,
    ``meta.purpose`` and per-column ``semantic_label`` merged in, so the discovered
    tables are passed through verbatim rather than rebuilt from our columns.
    """
    if tables is None:
        tables = list(link.extracted_tables.prefetch_related("columns", "rows"))
    else:
        tables = list(tables)
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
    result = _run_with_retries(
        "labeling",
        link,
        domtrack_client.label_tables,
        [_domtrack_table(table) for table in tables],
        config,
    )
    labeled_tables = (result or {}).get("tables") or []
    labels_to_create = []
    for table_index, table in enumerate(tables):
        entry = labeled_tables[table_index] if table_index < len(labeled_tables) else {}
        for column_index, column in enumerate(table.columns.all()):
            label = _column_label(entry, column_index)
            if not label:
                continue
            labels_to_create.append(
                SemanticLabel(
                    table=table,
                    column=column,
                    label=label,
                    provider=provider,
                    model=model,
                    language=language,
                )
            )
            labels.append(
                {
                    "table_id": table.pk,
                    "column_id": column.column_id,
                    "label": label,
                }
            )
    with transaction.atomic():
        # Scope the delete to the tables that were just relabeled; deleting every
        # label of the link would drop labels of tables that aren't recreated.
        SemanticLabel.objects.filter(table__in=tables).delete()
        SemanticLabel.objects.bulk_create(labels_to_create)
    call_count = math.ceil(len(tables) / max(1, int(config["batch_size"])))
    events.labeling_run(link, call_count, 0)
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


# ---------------------------------------------------------------------------
# US9 — publishing (FR-036..FR-038)
# ---------------------------------------------------------------------------


def publish_link_plans(link, actor=None):
    from apps.catalog.interfaces import CatalogInterface

    plans = list(link.plan_records.select_related("table"))
    if not plans:
        raise ValueError("plans_required")
    excluded = set(link.plan_exclusions.values_list("fingerprint", flat=True))
    published = 0
    seen_identities = set()
    for plan in plans:
        if (
            not _plan_is_complete(plan.values, plan.plan_type, plan.confidence)
            or plan_fingerprint(plan.plan_type, plan.values) in excluded
        ):
            continue
        identity = _plan_values_identity(plan.plan_type, plan.values)
        if identity in seen_identities:
            continue
        seen_identities.add(identity)
        CatalogInterface.upsert_published_record(
            source="admin_console",
            site=link.site_id,
            link=link.pk,
            trace=plan.table.trace_id,
            classification=plan.classification_id,
            plan_type=plan.plan_type,
            natural_key=plan.natural_key,
            values=_without_other(plan.values),
        )
        published += 1
    if not published and not all(
        plan_fingerprint(plan.plan_type, plan.values) in excluded for plan in plans
    ):
        raise ValueError("no_plan_records_met_quality_rules")
    link.pipeline_stage = Link.PipelineStage.PUBLISHED
    link.save(update_fields=["pipeline_stage", "updated_at"])
    events.published(link, published)
    return published


def retire_missing_plans(link, current_keys):
    """Retire this link's published records whose plan is no longer present (FR-038).

    Scoped to ``link``: ``current_keys`` only describes one link, so comparing it with
    the whole site's published keys would retire every other link's plans.
    ``CatalogInterface.published_natural_keys`` must accept ``link=``.
    """
    from apps.catalog.interfaces import CatalogInterface

    current = set(current_keys)
    published = CatalogInterface.published_natural_keys(
        site=link.site_id, link=link.pk
    )
    stale = [key for key in published if key not in current]
    for natural_key in stale:
        CatalogInterface.retire_published_record(
            source="admin_console", site=link.site_id, natural_key=natural_key
        )
    if stale:
        events.retired(link, len(stale))
    return len(stale)


# ---------------------------------------------------------------------------
# US10 — replay, failure rate, alerts, re-run (FR-039..FR-046)
# ---------------------------------------------------------------------------


def evaluate_failure_alert(link):
    threshold = constants.failure_rate_threshold()
    with transaction.atomic():
        # Serialise concurrent evaluations of the same link so they can't both
        # see "no open alert" and create two.
        Link.objects.select_for_update().filter(pk=link.pk).first()
        open_alert = link.failure_alerts.filter(state=FailureAlert.State.OPEN).first()
        if link.failure_rate >= threshold and open_alert is None:
            alert = FailureAlert.objects.create(
                link=link,
                state=FailureAlert.State.OPEN,
                failure_rate=link.failure_rate,
                raised_at=timezone.now(),
            )
            events.alert_raised(link, link.failure_rate)
            return alert
        if link.failure_rate < threshold and open_alert is not None:
            open_alert.state = FailureAlert.State.RESOLVED
            open_alert.resolved_at = timezone.now()
            open_alert.save(update_fields=["state", "resolved_at", "updated_at"])
        return open_alert


#: Failing stage (as recorded in ``Link.last_error``) → stage to resume from.
def _resume_stage_for(failed_stage, has_trace):
    stage = Link.PipelineStage
    resume = {
        "capture": stage.DISCOVERED,
        "extraction": stage.CAPTURED,
        "labeling": stage.EXTRACTED,
        "classification": stage.EXTRACTED,
        "schema_extraction": stage.EXTRACTED,
    }.get(failed_stage)
    if resume is None:
        resume = stage.CAPTURED if has_trace else stage.DISCOVERED
    if resume != stage.DISCOVERED and not has_trace:
        resume = stage.DISCOVERED
    return resume


def rerun_link_stages(link, actor=None):
    stage = Link.PipelineStage
    has_trace = bool(link.current_trace_id)
    if link.pipeline_stage == stage.DEAD_LETTERED:
        # last_error is "<stage>: <message>"
        failed = (link.last_error or "").split(":", 1)[0].strip()
        link.pipeline_stage = _resume_stage_for(failed, has_trace)
    elif link.pipeline_stage == stage.NO_PRICE_TABLES:
        # The tables were already extracted; re-run labeling + classification on the
        # stored tables rather than a fresh capture.
        link.pipeline_stage = stage.EXTRACTED
    elif link.pipeline_stage == stage.FLAGGED:
        # Extraction found no tables; try extracting again from the stored trace.
        link.pipeline_stage = stage.CAPTURED if has_trace else stage.DISCOVERED
    elif link.pipeline_stage == stage.AWAITING_LLM_BUDGET:
        awaiting = (link.last_error or "").rsplit(":", 1)[-1].strip()
        link.pipeline_stage = _resume_stage_for(awaiting, has_trace)
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
                "touches_price_table": change.touches_price_table,
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


def due_links(now=None, site_id=None):
    now = now or timezone.now()
    cutoff = now - timedelta(hours=constants.replay_period_hours())
    queryset = Link.objects.filter(
        is_active=True,
        review_state=Link.ReviewState.KEPT,
        site__maintenance_state=Site.MaintenanceState.ACTIVE,
        current_trace__isnull=False,  # replay needs a "before" trace
    )
    if site_id is not None:
        queryset = queryset.filter(site_id=site_id)
    return list(
        queryset.filter(models_q_last_replay(cutoff)).order_by(
            # Never-replayed links first (PostgreSQL sorts NULLs last by default).
            F("last_replay_at").asc(nulls_first=True)
        )[: constants.replay_batch_size()]
    )


def models_q_last_replay(cutoff):
    return Q(last_replay_at__isnull=True) | Q(last_replay_at__lt=cutoff)


def due_links_for_site(site_id, now=None):
    return due_links(now, site_id=site_id)


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


_FINISHED_RUN_STATES = (ReplayRun.State.SUCCEEDED, ReplayRun.State.FAILED)


def _recent_finished_run_states(link):
    """States of the link's latest finished runs.

    Scheduled/running/awaiting-budget runs have no outcome yet and would dilute the
    failure rate if counted.
    """
    return list(
        ReplayRun.objects.filter(link=link, state__in=_FINISHED_RUN_STATES)
        .order_by("-created_at")
        .values_list("state", flat=True)[: constants.failure_rate_window_runs()]
    )


def link_failure_payload(link):
    recent = _recent_finished_run_states(link)
    return {
        "link_id": link.pk,
        "failure_rate": link.failure_rate,
        "window_runs": len(recent),
        "threshold": constants.failure_rate_threshold(),
        "alert_state": (
            "open"
            if link.failure_alerts.filter(state=FailureAlert.State.OPEN).exists()
            else "none"
        ),
    }


def recompute_failure_rate(link):
    states = _recent_finished_run_states(link)
    if not states:
        link.failure_rate = 0.0
    else:
        failed = sum(1 for state in states if state == ReplayRun.State.FAILED)
        link.failure_rate = failed / len(states)
    link.save(update_fields=["failure_rate", "updated_at"])
    evaluate_failure_alert(link)
    return link.failure_rate


def metrics_snapshot():
    from apps.catalog.interfaces import CatalogInterface

    stage = Link.PipelineStage
    counts = Link.objects.aggregate(
        links_total=Count("pk"),
        links_published=Count("pk", filter=Q(pipeline_stage=stage.PUBLISHED)),
        links_awaiting_budget=Count(
            "pk", filter=Q(pipeline_stage=stage.AWAITING_LLM_BUDGET)
        ),
        links_dead_lettered=Count("pk", filter=Q(pipeline_stage=stage.DEAD_LETTERED)),
    )
    return {
        **counts,
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


def _run_with_retries(stage, target_link, fn, *args, **kwargs):
    """Run ``fn``; retry transient failures with backoff, dead-letter on exhaustion.

    * ``llm.LlmBudgetExhausted`` propagates untouched (the caller parks the link).
    * Network/provider errors (:func:`_retryable_errors`) are retried with linear
      backoff and the link is dead-lettered when attempts run out.
    * Anything else (bad input, parse errors, programming errors) is deterministic:
      it is recorded once as ``"<stage>: <message>"`` and re-raised immediately, so
      it neither blocks the worker with sleeps nor burns extra LLM calls.
    """
    attempts = max(1, constants.retry_max_attempts())
    retryable = _retryable_errors()
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            result = fn(*args, **kwargs)
            if target_link.retry_count or target_link.last_error:
                target_link.retry_count = 0
                target_link.last_error = ""
                target_link.save(
                    update_fields=["retry_count", "last_error", "updated_at"]
                )
            return result
        except llm.LlmBudgetExhausted:
            raise
        except retryable as exc:
            last_error = exc
            target_link.retry_count = attempt
            target_link.last_error = f"{stage}: {exc}"[:500]
            target_link.save(
                update_fields=["retry_count", "last_error", "updated_at"]
            )
            events.stage_failed(target_link, stage, str(exc)[:200])
            if attempt < attempts:
                _sleep(constants.retry_backoff_seconds() * attempt)
        except Exception as exc:  # noqa: BLE001 - deterministic failure, no retry
            target_link.last_error = f"{stage}: {exc}"[:500]
            target_link.save(update_fields=["last_error", "updated_at"])
            events.stage_failed(target_link, stage, str(exc)[:200])
            raise
    Link.objects.filter(pk=target_link.pk).update(
        pipeline_stage=Link.PipelineStage.DEAD_LETTERED,
        updated_at=timezone.now(),
    )
    target_link.pipeline_stage = Link.PipelineStage.DEAD_LETTERED
    raise last_error


def classify_and_extract_link_tables(link, actor=None):
    """Backward-compatible name for the combined classify-and-extract pass."""
    return process_link_tables(link, actor=actor)