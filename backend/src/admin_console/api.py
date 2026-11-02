"""DRF views for the operator console API, mounted at /api/v1/ops/."""

from drf_spectacular.utils import extend_schema
from django.db.models import Count
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import selectors as account_selectors
from accounts.exceptions import ApiError
from admin_console import domtrack_client, events, llm, serializers, services
from admin_console.models import CaptureSession, FailureAlert, Link, Site
from admin_console.serializers import (
    ApprovalQueueSerializer,
    CaptureStartInput,
    ClassifyInput,
    ConsoleErrorSerializer,
    DiscoverLinksInput,
    ManualLinksInput,
    PlanIgnoreInput,
    PlansInput,
    ReplayRunInput,
    SiteCreateInput,
    TokenBudgetInput,
    VerificationDecisionInput,
    VerificationDecisionInputSerializer,
    parse_input,
)


class AuthenticatedView(APIView):
    """Base view resolving the JWT caller and refusing guests."""

    def caller(self, request):
        user = account_selectors.user_from_request(request)
        if user is None:
            raise ApiError(
                "not_authenticated", "Authentication is required.", http_status=401
            )
        return user


class OperatorOnlyView(AuthenticatedView):
    """Base view requiring an operator role (``ops`` group or admin, FR-001, FR-005)."""

    def caller(self, request):
        user = super().caller(request)
        if not user.is_operator():
            raise ApiError(
                "admin_required",
                "This action is restricted to operators.",
                http_status=403,
            )
        return user


def _site_payload(site):
    return {
        "id": site.pk,
        "company_id": site.company_id,
        "domain": site.domain,
        "maintenance_state": site.maintenance_state,
        "onboarded_at": site.onboarded_at.isoformat() if site.onboarded_at else None,
    }


def _link_payload(link):
    return {
        "id": link.pk,
        "site_id": link.site_id,
        "url": link.url,
        "source": link.source,
        "review_state": link.review_state,
        "pipeline_stage": link.pipeline_stage,
        "failure_rate": link.failure_rate,
        "current_trace_id": link.current_trace_id,
        "last_error": link.last_error,
        "pipeline_task_state": link.pipeline_task_state,
    }


def _site_link_payloads(queryset):
    return list(
        queryset.order_by("-created_at").values(
            "id",
            "site_id",
            "url",
            "source",
            "review_state",
            "pipeline_stage",
            "failure_rate",
            "current_trace_id",
            "last_error",
            "pipeline_task_state",
        )
    )


def get_site_or_error(site_id):
    site = Site.objects.filter(pk=site_id).first()
    if site is None:
        raise ApiError("not_found", "Site not found.", http_status=404)
    return site


def get_link_or_error(link_id):
    link = Link.objects.filter(pk=link_id).first()
    if link is None:
        raise ApiError("not_found", "Link not found.", http_status=404)
    return link


def _stage_error(exc):
    """Map a stage exception onto the console error contract."""
    if isinstance(exc, llm.LlmBudgetExhausted):
        return ApiError(
            "awaiting_llm_budget",
            "The LLM token budget is exhausted; the work will resume when it is restored.",
            http_status=202,
        )
    if isinstance(exc, PermissionError):
        return ApiError("labeling_disabled", str(exc), http_status=403)
    if isinstance(exc, domtrack_client.DomtrackCaptureError):
        return ApiError(
            "dead_lettered",
            "Capture failed after retries; the link did not advance.",
            http_status=502,
        )
    if isinstance(exc, RuntimeError) and str(exc) == "capture_in_progress":
        return ApiError(
            "capture_in_progress", "A capture is already in flight.", http_status=409
        )
    message = str(exc)
    if message in ("trace_required", "no_tables_found", "plans_required"):
        return ApiError(
            message, "The link is not ready for this stage.", http_status=409
        )
    if message == "link_not_ready":
        return ApiError(
            "link_not_ready", "The link is not ready for this stage.", http_status=400
        )
    return ApiError("invalid_field", message[:200], http_status=400)


# ---------------------------------------------------------------------------
# US1 — approval queue (FR-001..FR-006)
# ---------------------------------------------------------------------------


class ApprovalQueueView(OperatorOnlyView):
    @extend_schema(responses={200: ApprovalQueueSerializer})
    def get(self, request):
        self.caller(request)
        results = services.approval_queue()
        return Response({"results": results, "count": len(results)})


class VerificationDecisionView(OperatorOnlyView):
    @extend_schema(
        request=VerificationDecisionInputSerializer,
        responses={201: dict, 400: ConsoleErrorSerializer, 403: ConsoleErrorSerializer},
    )
    def post(self, request, company_id):
        actor = self.caller(request)
        payload = parse_input(VerificationDecisionInput, request.data)
        company, decision, site = services.record_decision(
            company_id, actor, payload.outcome, note=payload.note or ""
        )
        return Response(
            {
                "company": {
                    "id": company.pk,
                    "verification_status": company.verification_status,
                },
                "decision": {
                    "outcome": decision.outcome,
                    "actor_id": getattr(decision, "actor_id", actor.pk),
                    "decided_at": getattr(decision, "decided_at", None)
                    and decision.decided_at.isoformat(),
                    "note": getattr(decision, "note", ""),
                },
                "site": _site_payload(site) if site else None,
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# US2 — automated link discovery (FR-007..FR-011)
# ---------------------------------------------------------------------------


class SiteCreateView(OperatorOnlyView):
    def get(self, request):
        self.caller(request)
        sites = Site.objects.select_related("company")
        results = []
        for site in sites:
            stage_rows = (
                Link.objects.filter(site=site)
                .values("pipeline_stage")
                .annotate(count=Count("pk"))
            )
            stage_counts = {stage: 0 for stage, _ in Link.PipelineStage.choices}
            stage_counts.update(
                {row["pipeline_stage"]: row["count"] for row in stage_rows}
            )
            results.append(
                {
                    **_site_payload(site),
                    "company_name": site.company.company_name,
                    "links_count": sum(stage_counts.values()),
                    "stage_counts": stage_counts,
                }
            )
        return Response({"results": results, "count": len(results)})

    @extend_schema(
        request=SiteCreateInput, responses={201: dict, 409: ConsoleErrorSerializer}
    )
    def post(self, request):
        actor = self.caller(request)
        payload = parse_input(SiteCreateInput, request.data)
        if Site.objects.filter(company_id=payload.company_id).exists():
            raise ApiError(
                "invalid_field",
                "The company already has a site.",
                http_status=409,
                fields={"company_id": "already onboarded"},
            )
        site = services.onboard_site(payload.company_id, actor=actor)
        return Response({"site": _site_payload(site)}, status=status.HTTP_201_CREATED)


class SiteDetailView(OperatorOnlyView):
    def get(self, request, site_id):
        self.caller(request)
        site = get_site_or_error(site_id)
        links = _site_link_payloads(Link.objects.filter(site=site))
        return Response({"site": _site_payload(site), "links": links})


class DiscoverLinksView(OperatorOnlyView):
    @extend_schema(
        request=DiscoverLinksInput, responses={200: dict, 502: ConsoleErrorSerializer}
    )
    def post(self, request, site_id):
        self.caller(request)
        site = get_site_or_error(site_id)
        payload = (
            parse_input(DiscoverLinksInput, request.data) if request.data else None
        )
        bounds = {}
        if payload is not None:
            bounds = {"max_pages": payload.max_pages, "max_depth": payload.max_depth}
        try:
            result = services.discover_and_store_links(site, bounds=bounds)
        except Exception as exc:  # noqa: BLE001 - crawl/network failure
            raise ApiError("crawl_failed", str(exc)[:200], http_status=502) from exc
        if result["links"]:
            from admin_console.tasks import run_site_pipeline_task

            transaction.on_commit(
                lambda: run_site_pipeline_task.enqueue(site.pk, discover=False)
            )
        return Response(
            {
                "site": _site_payload(site),
                "discovered": result["discovered"],
                "after_policy": result["after_policy"],
                "candidates": [_link_payload(link) for link in result["links"]],
            }
        )


class SiteLinksView(OperatorOnlyView):
    def get(self, request, site_id):
        self.caller(request)
        site = get_site_or_error(site_id)
        qs = site.links.all()
        review_state = request.query_params.get("review_state")
        if review_state:
            qs = qs.filter(review_state=review_state)
        links = _site_link_payloads(qs)
        return Response({"site_id": site.pk, "links": links, "count": len(links)})

    def post(self, request, site_id):
        actor = self.caller(request)
        site = get_site_or_error(site_id)
        payload = parse_input(ManualLinksInput, request.data)
        links = services.add_links_manually(site, payload.urls, actor=actor)
        return Response(
            {"results": [_link_payload(link) for link in links]},
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# US4 — server-side headless capture (FR-016..FR-019)
# ---------------------------------------------------------------------------


def _capture_payload(session):
    return {
        "id": session.pk,
        "link_id": session.link_id,
        "state": session.state,
        "mode": session.mode,
        "duration_ms": session.duration_ms,
        "error": session.error,
        "trace_id": session.trace_id,
    }


class CaptureStartView(OperatorOnlyView):
    @extend_schema(request=CaptureStartInput, responses={201: dict})
    def post(self, request, link_id):
        self.caller(request)
        link = get_link_or_error(link_id)
        payload = parse_input(CaptureStartInput, request.data) if request.data else None
        try:
            session = services.start_capture(
                link, duration_ms=payload.duration_ms if payload else None
            )
        except Exception as exc:  # noqa: BLE001
            raise _stage_error(exc) from exc
        return Response(
            {"capture_session": _capture_payload(session), "link": _link_payload(link)},
            status=status.HTTP_201_CREATED,
        )


class LinkCaptureListView(OperatorOnlyView):
    def get(self, request, link_id):
        self.caller(request)
        link = get_link_or_error(link_id)
        sessions = link.capture_sessions.all()
        return Response({"results": [_capture_payload(s) for s in sessions]})


class CaptureFailView(OperatorOnlyView):
    def post(self, request, capture_session_id):
        self.caller(request)
        session = CaptureSession.objects.filter(pk=capture_session_id).first()
        if session is None:
            raise ApiError("not_found", "Capture session not found.", http_status=404)
        services.fail_capture(session, request.data.get("error", "failed"))
        return Response({"capture_session": _capture_payload(session)})


# ---------------------------------------------------------------------------
# US5 — table extraction (FR-020..FR-022)
# ---------------------------------------------------------------------------


class ExtractionView(OperatorOnlyView):
    @extend_schema(responses={201: dict, 409: ConsoleErrorSerializer})
    def post(self, request, link_id):
        self.caller(request)
        link = get_link_or_error(link_id)
        try:
            tables = services.extract_link_tables(link)
        except Exception as exc:  # noqa: BLE001
            raise _stage_error(exc) from exc
        return Response(
            {
                "extraction": {
                    "trace_id": link.current_trace_id,
                    "table_count": len(tables),
                },
                "link": _link_payload(link),
            },
            status=status.HTTP_201_CREATED if tables else status.HTTP_200_OK,
        )


class LinkTablesView(OperatorOnlyView):
    def get(self, request, link_id):
        self.caller(request)
        link = get_link_or_error(link_id)
        return Response({"tables": services.tables_payload(link)})


# ---------------------------------------------------------------------------
# US6 — table classification (FR-023..FR-025)
# ---------------------------------------------------------------------------


class ClassificationView(OperatorOnlyView):
    @extend_schema(
        request=ClassifyInput, responses={200: dict, 202: ConsoleErrorSerializer}
    )
    def post(self, request, link_id):
        self.caller(request)
        link = get_link_or_error(link_id)
        try:
            services.classify_tables_for_link(link)
        except Exception as exc:  # noqa: BLE001
            raise _stage_error(exc) from exc
        return Response(
            {
                "classifications": services.table_classifications_payload(link),
                "link": _link_payload(link),
            }
        )

    def get(self, request, link_id):
        self.caller(request)
        link = get_link_or_error(link_id)
        return Response({"classifications": services.table_classifications_payload(link)})


# ---------------------------------------------------------------------------
# US7 — plan schema extraction (FR-026..FR-031)
# ---------------------------------------------------------------------------


class PlanSchemaView(OperatorOnlyView):
    def get(self, request):
        from admin_console import plan_schema

        self.caller(request)
        plan_type = request.query_params.get("plan_type", "hosting")
        plan = plan_schema.schema_for(plan_type)
        if plan is None:
            raise ApiError("not_found", "Unknown plan type.", http_status=404)
        return Response(
            {
                "plan_type": plan.key,
                "label": plan.label,
                "fields": [
                    {
                        "key": field.key,
                        "label": field.label,
                        "kind": field.kind,
                        "required": field.required,
                        "values": list(field.values),
                    }
                    for field in plan.fields
                ],
            }
        )


class PlansView(OperatorOnlyView):
    @extend_schema(
        request=PlansInput, responses={201: dict, 202: ConsoleErrorSerializer}
    )
    def post(self, request, link_id):
        self.caller(request)
        link = get_link_or_error(link_id)
        try:
            if not link.plan_records.exists() and link.pipeline_stage in (
                Link.PipelineStage.EXTRACTED,
                Link.PipelineStage.NO_PRICE_TABLES,
            ):
                services.process_link_tables(link)
                if not link.plan_records.exists():
                    raise ValueError("plans_required")
        except Exception as exc:  # noqa: BLE001
            raise _stage_error(exc) from exc
        return Response(
            {"plans": services.plans_payload(link), "link": _link_payload(link)},
            status=status.HTTP_201_CREATED,
        )

    def get(self, request, link_id):
        self.caller(request)
        link = get_link_or_error(link_id)
        return Response({"plans": services.plans_payload(link)})


class PlanIgnoreView(OperatorOnlyView):
    @extend_schema(request=PlanIgnoreInput, responses={200: dict})
    def put(self, request, link_id, plan_id):
        self.caller(request)
        link = get_link_or_error(link_id)
        plan = link.plan_records.filter(pk=plan_id).first()
        if plan is None:
            return Response(
                {"error": {"code": "plan_not_found"}},
                status=status.HTTP_404_NOT_FOUND,
            )
        values = parse_input(PlanIgnoreInput, request.data)
        ignored = services.set_plan_excluded(link, plan, values.ignored)
        return Response({"plan_id": plan.pk, "ignored": ignored})


# ---------------------------------------------------------------------------
# US8 — optional labeling (FR-032..FR-035)
# ---------------------------------------------------------------------------


class LabelingView(OperatorOnlyView):
    @extend_schema(
        responses={200: dict, 403: ConsoleErrorSerializer, 202: ConsoleErrorSerializer}
    )
    def post(self, request, link_id):
        self.caller(request)
        link = get_link_or_error(link_id)
        try:
            labels = services.label_link_tables(link)
        except Exception as exc:  # noqa: BLE001
            raise _stage_error(exc) from exc
        return Response({"labels": labels, "labeled_tables": len(labels)})


# ---------------------------------------------------------------------------
# US9 — publishing (FR-036..FR-038)
# ---------------------------------------------------------------------------


class PublishView(OperatorOnlyView):
    @extend_schema(responses={200: dict, 409: ConsoleErrorSerializer})
    def post(self, request, link_id):
        self.caller(request)
        link = get_link_or_error(link_id)
        try:
            published = services.publish_link_plans(link)
        except Exception as exc:  # noqa: BLE001
            raise _stage_error(exc) from exc
        return Response({"published": published, "link": _link_payload(link)})


# ---------------------------------------------------------------------------
# US10 — replay, failure, alerts, re-run (FR-039..FR-046)
# ---------------------------------------------------------------------------


class ReplayRunListView(OperatorOnlyView):
    def get(self, request):
        self.caller(request)
        runs = services.replay_runs(
            link_id=request.query_params.get("link_id"),
            state=request.query_params.get("state"),
        )
        return Response({"results": [services.replay_run_payload(r) for r in runs]})


class ReplayRunCreateView(OperatorOnlyView):
    @extend_schema(request=ReplayRunInput, responses={202: dict})
    def post(self, request):
        from admin_console import tasks

        self.caller(request)
        payload = parse_input(ReplayRunInput, request.data)
        if payload.link_ids:
            links = list(Link.objects.filter(pk__in=payload.link_ids))
        elif payload.site_id:
            links = services.due_links_for_site(payload.site_id)
        else:
            links = services.due_links()
        for link in links:
            tasks.run_replay_task.enqueue(link.pk)
        return Response({"enqueued": len(links)}, status=status.HTTP_202_ACCEPTED)


class LinkFailureView(OperatorOnlyView):
    def get(self, request, link_id):
        self.caller(request)
        return Response(services.link_failure_payload(get_link_or_error(link_id)))


class AlertListView(OperatorOnlyView):
    def get(self, request):
        self.caller(request)
        alerts = services.alerts(state=request.query_params.get("state"))
        return Response({"results": [services.alert_payload(a) for a in alerts]})


class LinkRerunView(OperatorOnlyView):
    def post(self, request, link_id):
        from django.db import transaction
        from django.tasks.base import TASK_MAX_PRIORITY

        from admin_console.tasks import run_site_pipeline_task

        actor = self.caller(request)
        with transaction.atomic():
            get_link_or_error(link_id)
            link = Link.objects.select_for_update().get(pk=link_id)
            if link.pipeline_task_state in ("queued", "running"):
                return Response(
                    {"link": _link_payload(link), "queued": True},
                    status=status.HTTP_202_ACCEPTED,
                )
            link = services.rerun_link_stages(link, actor=actor)
            link.pipeline_task_state = "queued"
            link.save(update_fields=["pipeline_task_state", "updated_at"])
            transaction.on_commit(
                lambda site_id=link.site_id, retry_link_id=link.pk: run_site_pipeline_task.using(
                    priority=TASK_MAX_PRIORITY
                ).enqueue(
                    site_id, discover=False, link_id=retry_link_id
                )
            )
        return Response(
            {"link": _link_payload(link), "queued": True},
            status=status.HTTP_202_ACCEPTED,
        )


# ---------------------------------------------------------------------------
# Settings and observability (FR-047, FR-054..FR-057)
# ---------------------------------------------------------------------------


class SettingsView(OperatorOnlyView):
    def get(self, request):
        self.caller(request)
        return Response({"values": _settings_snapshot()})

    def put(self, request):
        from constance import config

        self.caller(request)
        values = request.data.get("values") or {}
        updated = {}
        for key, value in values.items():
            if hasattr(config, key):
                setattr(config, key, value)
                updated[key] = value
        return Response({"values": updated})


def _settings_snapshot():
    from admin_console import constants

    return {
        "REPLAY_PERIOD_HOURS": constants.replay_period_hours(),
        "FAILURE_RATE_THRESHOLD": constants.failure_rate_threshold(),
        "LINK_CRAWL_MAX_PAGES": constants.link_crawl_max_pages(),
        "LINK_DENY_EXTENSIONS": constants.link_deny_extensions(),
        "LINK_DENY_SEGMENTS": constants.link_deny_segments(),
        "CAPTURE_FIXED_DURATION_MS": constants.capture_fixed_duration_ms(),
        "LABELING_PROVIDER": constants.labeling_provider(),
        "LABELING_MODEL": constants.labeling_model() or "",
    }


class TokenBudgetView(OperatorOnlyView):
    def get(self, request):
        self.caller(request)
        return Response(services.token_budget_status())

    @extend_schema(request=TokenBudgetInput, responses={200: dict})
    def put(self, request):
        actor = self.caller(request)
        payload = parse_input(TokenBudgetInput, request.data)
        if payload.token_budget is not None:
            services.set_token_budget(
                payload.token_budget, period=payload.period, actor=actor
            )
        return Response(services.token_budget_status(period=payload.period))


class MetricsView(OperatorOnlyView):
    def get(self, request):
        self.caller(request)
        return Response(services.metrics_snapshot())
