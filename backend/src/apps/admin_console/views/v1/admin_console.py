"""DRF viewsets for the operator console API, mounted at /api/v1/ops/."""

from django.db import transaction
from django.db.models import Count
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts import selectors as account_selectors
from apps.accounts.exceptions import ApiError
from apps.admin_console import services
from apps.admin_console.serializers import (
    AlertListSerializer,
    ApprovalQueueSerializer,
    CaptureFailInputSerializer,
    CaptureFailSerializer,
    CaptureListSerializer,
    CaptureSessionSerializer,
    CaptureStartInputSerializer,
    CaptureStartSerializer,
    ClassificationSerializer,
    ClassifyInputSerializer,
    ConsoleErrorSerializer,
    DiscoverLinksInputSerializer,
    DiscoverLinksSerializer,
    ExtractionSerializer,
    LabelingSerializer,
    LinkFailureSerializer,
    LinkListSerializer,
    LinkSerializer,
    ManualLinksInputSerializer,
    MetricsSerializer,
    PlanIgnoreInputSerializer,
    PlanIgnoreSerializer,
    PlanSchemaSerializer,
    PlansInputSerializer,
    PlansSerializer,
    PublishSerializer,
    RerunSerializer,
    ReplayEnqueueSerializer,
    ReplayRunInputSerializer,
    ReplayRunListSerializer,
    SettingsSerializer,
    SettingsUpdateInputSerializer,
    SiteCreateInputSerializer,
    SiteDetailSerializer,
    SiteLinksSerializer,
    SiteListSerializer,
    SiteSerializer,
    TablesSerializer,
    TokenBudgetInputSerializer,
    TokenBudgetSerializer,
    VerificationDecisionInputSerializer,
    VerificationDecisionResultSerializer,
)
from apps.pipeline import domtrack_client, events, llm
from apps.pipeline.interfaces import PipelineInterface, TaskBackendUnavailable
from apps.pipeline.services.v1 import pipeline as pipeline_services
from apps.utils.serializers import parse_input


class OperatorViewSet(GenericViewSet):
    """Base viewset resolving the JWT caller and requiring the operator role."""

    def caller(self, request):
        user = account_selectors.user_from_request(request)
        if user is None:
            raise ApiError(
                "not_authenticated", "Authentication is required.", http_status=401
            )
        if not user.is_operator():
            raise ApiError(
                "admin_required",
                "This action is restricted to operators.",
                http_status=403,
            )
        return user

    def _site(self, site_id):
        try:
            return PipelineInterface.site_or_error(site_id)
        except LookupError as exc:
            raise ApiError("not_found", "Site not found.", http_status=404) from exc

    def _link(self, link_id):
        try:
            return PipelineInterface.link_or_error(link_id)
        except LookupError as exc:
            raise ApiError("not_found", "Link not found.", http_status=404) from exc

    def _session(self, session_id):
        try:
            return PipelineInterface.capture_session_or_error(session_id)
        except LookupError as exc:
            raise ApiError(
                "not_found", "Capture session not found.", http_status=404
            ) from exc


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


def _stage_error(exc):
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
    if isinstance(exc, llm.NoPlanRecordsError):
        return ApiError(
            "plans_required",
            "No plan records met the extraction rules.",
            http_status=409,
        )
    if message in ("trace_required", "no_tables_found", "plans_required"):
        return ApiError(message, "The link is not ready for this stage.", http_status=409)
    if message == "link_not_ready":
        return ApiError(
            "link_not_ready", "The link is not ready for this stage.", http_status=400
        )
    return ApiError("invalid_field", message[:200], http_status=400)


def _task_error(exc):
    if isinstance(exc, TaskBackendUnavailable):
        return ApiError(
            "task_backend_unavailable",
            "The task backend is unavailable. Nothing was queued.",
            http_status=503,
        )
    return _stage_error(exc)


class OpsViewSet(OperatorViewSet):
    """All operator console endpoints as generic-viewset actions."""

    # US1 — approval queue
    @extend_schema(responses={200: ApprovalQueueSerializer})
    @action(detail=False, methods=["get"], url_path="approvals")
    def approvals(self, request):
        self.caller(request)
        results = services.approval_queue()
        return Response(
            ApprovalQueueSerializer({"results": results, "count": len(results)}).data
        )

    @extend_schema(
        request=VerificationDecisionInputSerializer,
        responses={201: VerificationDecisionResultSerializer},
    )
    @action(
        detail=False,
        methods=["post"],
        url_path=r"companies/(?P<company_id>\d+)/verification-decisions",
    )
    def verification_decisions(self, request, company_id):
        actor = self.caller(request)
        payload = parse_input(VerificationDecisionInputSerializer, request.data)
        try:
            company, decision, site = services.record_decision(
                company_id, actor, payload["outcome"], note=payload.get("note", "")
            )
        except TaskBackendUnavailable as exc:
            raise _task_error(exc) from exc
        body = {
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
        }
        return Response(
            VerificationDecisionResultSerializer(body).data,
            status=status.HTTP_201_CREATED,
        )

    # US2 — sites and links
    @extend_schema(responses={200: SiteListSerializer})
    @action(detail=False, methods=["get", "post"], url_path="sites")
    def sites(self, request):
        actor = self.caller(request)
        if request.method == "POST":
            payload = parse_input(SiteCreateInputSerializer, request.data)
            if PipelineInterface.site_for_company(payload["company_id"]) is not None:
                raise ApiError(
                    "invalid_field",
                    "The company already has a site.",
                    http_status=409,
                    fields={"company_id": "already onboarded"},
                )
            try:
                site = PipelineInterface.onboard_site(
                    payload["company_id"], actor=actor
                )
            except TaskBackendUnavailable as exc:
                raise _task_error(exc) from exc
            return Response(
                {"site": _site_payload(site)}, status=status.HTTP_201_CREATED
            )
        results = []
        for site in PipelineInterface.all_sites():
            stage_rows = (
                site.links.values("pipeline_stage").annotate(count=Count("pk"))
            )
            stage_counts = {stage: 0 for stage, _ in site.links.model.PipelineStage.choices}
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
        return Response(
            SiteListSerializer({"results": results, "count": len(results)}).data
        )

    @extend_schema(responses={200: SiteDetailSerializer})
    @action(detail=False, methods=["get"], url_path=r"sites/(?P<site_id>\d+)")
    def site_detail(self, request, site_id):
        self.caller(request)
        site = self._site(site_id)
        links = [_link_payload(link) for link in PipelineInterface.site_links(site)]
        return Response(SiteDetailSerializer({"site": _site_payload(site), "links": links}).data)

    @extend_schema(
        request=DiscoverLinksInputSerializer, responses={200: DiscoverLinksSerializer}
    )
    @action(
        detail=False,
        methods=["post"],
        url_path=r"sites/(?P<site_id>\d+)/discover-links",
    )
    def discover_links(self, request, site_id):
        actor = self.caller(request)
        site = self._site(site_id)
        payload = (
            parse_input(DiscoverLinksInputSerializer, request.data)
            if request.data
            else {}
        )
        bounds = {
            "max_pages": payload.get("max_pages"),
            "max_depth": payload.get("max_depth"),
        }
        try:
            result = pipeline_services.discover_and_store_links(
                site, actor=actor, bounds=bounds
            )
        except Exception as exc:  # noqa: BLE001 - crawl/network failure
            raise ApiError("crawl_failed", str(exc)[:200], http_status=502) from exc
        if result["links"]:
            try:
                PipelineInterface.enqueue_site_pipeline(
                    site.pk, actor=actor, discover=False
                )
            except TaskBackendUnavailable as exc:
                raise _task_error(exc) from exc
        body = {
            "site": _site_payload(site),
            "discovered": result["discovered"],
            "after_policy": result["after_policy"],
            "candidates": [_link_payload(link) for link in result["links"]],
        }
        return Response(DiscoverLinksSerializer(body).data)

    @extend_schema(responses={200: SiteLinksSerializer})
    @action(
        detail=False, methods=["get", "post"], url_path=r"sites/(?P<site_id>\d+)/links"
    )
    def site_links(self, request, site_id):
        actor = self.caller(request)
        site = self._site(site_id)
        if request.method == "POST":
            payload = parse_input(ManualLinksInputSerializer, request.data)
            links = pipeline_services.add_links_manually(
                site, payload["urls"], actor=actor
            )
            return Response(
                LinkListSerializer(
                    {"results": [_link_payload(link) for link in links]}
                ).data,
                status=status.HTTP_201_CREATED,
            )
        links = [
            _link_payload(link)
            for link in PipelineInterface.site_links(
                site, review_state=request.query_params.get("review_state")
            )
        ]
        return Response(
            SiteLinksSerializer(
                {"site_id": site.pk, "links": links, "count": len(links)}
            ).data
        )

    # US4 — capture
    @extend_schema(
        request=CaptureStartInputSerializer, responses={201: CaptureStartSerializer}
    )
    @action(
        detail=False, methods=["post"], url_path=r"links/(?P<link_id>\d+)/captures"
    )
    def capture_start(self, request, link_id):
        actor = self.caller(request)
        link = self._link(link_id)
        payload = (
            parse_input(CaptureStartInputSerializer, request.data)
            if request.data
            else {}
        )
        try:
            session = pipeline_services.start_capture(
                link, actor=actor, duration_ms=payload.get("duration_ms")
            )
        except Exception as exc:  # noqa: BLE001
            raise _stage_error(exc) from exc
        return Response(
            CaptureStartSerializer(
                {
                    "capture_session": _capture_payload(session),
                    "link": _link_payload(link),
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(responses={200: CaptureListSerializer})
    @action(
        detail=False,
        methods=["get"],
        url_path=r"links/(?P<link_id>\d+)/captures/list",
    )
    def capture_list(self, request, link_id):
        self.caller(request)
        link = self._link(link_id)
        sessions = [
            _capture_payload(session)
            for session in PipelineInterface.link_capture_sessions(link)
        ]
        return Response(CaptureListSerializer({"results": sessions}).data)

    @extend_schema(
        request=CaptureFailInputSerializer, responses={200: CaptureFailSerializer}
    )
    @action(
        detail=False,
        methods=["post"],
        url_path=r"captures/(?P<capture_session_id>\d+)/fail",
    )
    def capture_fail(self, request, capture_session_id):
        self.caller(request)
        session = self._session(capture_session_id)
        payload = parse_input(CaptureFailInputSerializer, request.data)
        pipeline_services.fail_capture(session, payload["error"])
        return Response(
            CaptureFailSerializer({"capture_session": _capture_payload(session)}).data
        )

    # US5 — extraction
    @extend_schema(responses={201: ExtractionSerializer})
    @action(
        detail=False, methods=["post"], url_path=r"links/(?P<link_id>\d+)/extractions"
    )
    def extraction(self, request, link_id):
        actor = self.caller(request)
        link = self._link(link_id)
        try:
            tables = pipeline_services.extract_link_tables(link, actor=actor)
        except Exception as exc:  # noqa: BLE001
            raise _stage_error(exc) from exc
        body = {
            "extraction": {
                "trace_id": link.current_trace_id,
                "table_count": len(tables),
            },
            "link": _link_payload(link),
        }
        return Response(
            ExtractionSerializer(body).data,
            status=status.HTTP_201_CREATED if tables else status.HTTP_200_OK,
        )

    @extend_schema(responses={200: TablesSerializer})
    @action(detail=False, methods=["get"], url_path=r"links/(?P<link_id>\d+)/tables")
    def tables(self, request, link_id):
        self.caller(request)
        link = self._link(link_id)
        return Response(
            TablesSerializer({"tables": pipeline_services.tables_payload(link)}).data
        )

    # US6 — classification
    @extend_schema(request=ClassifyInputSerializer, responses={200: ClassificationSerializer})
    @action(
        detail=False,
        methods=["get", "post"],
        url_path=r"links/(?P<link_id>\d+)/classifications",
    )
    def classifications(self, request, link_id):
        actor = self.caller(request)
        link = self._link(link_id)
        if request.method == "POST":
            parse_input(ClassifyInputSerializer, request.data)
            try:
                pipeline_services.classify_tables_for_link(link, actor=actor)
            except Exception as exc:  # noqa: BLE001
                raise _stage_error(exc) from exc
            body = {
                "classifications": pipeline_services.table_classifications_payload(link),
                "link": _link_payload(link),
            }
            return Response(ClassificationSerializer(body).data)
        return Response(
            ClassificationSerializer(
                {"classifications": pipeline_services.table_classifications_payload(link)}
            ).data
        )

    # US7 — plans
    @extend_schema(responses={200: PlanSchemaSerializer})
    @action(detail=False, methods=["get"], url_path="plan-schema")
    def plan_schema(self, request):
        from apps.pipeline import plan_schema

        self.caller(request)
        plan_type = request.query_params.get("plan_type", "hosting")
        plan = plan_schema.schema_for(plan_type)
        if plan is None:
            raise ApiError("not_found", "Unknown plan type.", http_status=404)
        body = {
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
        return Response(PlanSchemaSerializer(body).data)

    @extend_schema(request=PlansInputSerializer, responses={201: PlansSerializer})
    @action(
        detail=False, methods=["get", "post"], url_path=r"links/(?P<link_id>\d+)/plans"
    )
    def plans(self, request, link_id):
        actor = self.caller(request)
        link = self._link(link_id)
        if request.method == "POST":
            parse_input(PlansInputSerializer, request.data)
            try:
                if not PipelineInterface.link_plans(link).exists() and link.pipeline_stage in (
                    link.PipelineStage.EXTRACTED,
                    link.PipelineStage.NO_PRICE_TABLES,
                ):
                    pipeline_services.process_link_tables(link, actor=actor)
                    if not PipelineInterface.link_plans(link).exists():
                        raise ValueError("plans_required")
            except Exception as exc:  # noqa: BLE001
                raise _stage_error(exc) from exc
            return Response(
                PlansSerializer(
                    {
                        "plans": pipeline_services.plans_payload(link),
                        "link": _link_payload(link),
                    }
                ).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(
            PlansSerializer({"plans": pipeline_services.plans_payload(link)}).data
        )

    @extend_schema(request=PlanIgnoreInputSerializer, responses={200: PlanIgnoreSerializer})
    @action(
        detail=False,
        methods=["put"],
        url_path=r"links/(?P<link_id>\d+)/plans/(?P<plan_id>\d+)/ignore",
    )
    def plan_ignore(self, request, link_id, plan_id):
        self.caller(request)
        link = self._link(link_id)
        plan = PipelineInterface.link_plans(link).filter(pk=plan_id).first()
        if plan is None:
            raise ApiError("plan_not_found", "Plan not found.", http_status=404)
        payload = parse_input(PlanIgnoreInputSerializer, request.data)
        ignored = pipeline_services.set_plan_excluded(link, plan, payload["ignored"])
        return Response(
            PlanIgnoreSerializer({"plan_id": plan.pk, "ignored": ignored}).data
        )

    # US8 — labeling
    @extend_schema(responses={200: LabelingSerializer})
    @action(
        detail=False, methods=["post"], url_path=r"links/(?P<link_id>\d+)/labeling"
    )
    def labeling(self, request, link_id):
        actor = self.caller(request)
        link = self._link(link_id)
        try:
            labels = pipeline_services.label_link_tables(link, actor=actor)
        except Exception as exc:  # noqa: BLE001
            raise _stage_error(exc) from exc
        return Response(
            LabelingSerializer(
                {"labels": labels, "labeled_tables": len(labels)}
            ).data
        )

    # US9 — publishing
    @extend_schema(responses={200: PublishSerializer})
    @action(
        detail=False, methods=["post"], url_path=r"links/(?P<link_id>\d+)/publish"
    )
    def publish(self, request, link_id):
        actor = self.caller(request)
        link = self._link(link_id)
        try:
            published = pipeline_services.publish_link_plans(link, actor=actor)
        except Exception as exc:  # noqa: BLE001
            raise _stage_error(exc) from exc
        return Response(
            PublishSerializer(
                {"published": published, "link": _link_payload(link)}
            ).data
        )

    # US10 — replay, failure, alerts, rerun
    @extend_schema(responses={200: ReplayRunListSerializer})
    @action(detail=False, methods=["get"], url_path="replay-runs")
    def replay_runs(self, request):
        self.caller(request)
        runs = pipeline_services.replay_runs(
            link_id=request.query_params.get("link_id"),
            state=request.query_params.get("state"),
        )
        return Response(
            ReplayRunListSerializer(
                {"results": [pipeline_services.replay_run_payload(r) for r in runs]}
            ).data
        )

    @extend_schema(
        request=ReplayRunInputSerializer, responses={202: ReplayEnqueueSerializer}
    )
    @action(detail=False, methods=["post"], url_path="replay-runs/create")
    def replay_create(self, request):
        actor = self.caller(request)
        payload = parse_input(ReplayRunInputSerializer, request.data)
        if payload.get("link_ids"):
            links = list(
                PipelineInterface.link_queryset().filter(pk__in=payload["link_ids"])
            )
        elif payload.get("site_id"):
            links = pipeline_services.due_links_for_site(payload["site_id"])
        else:
            links = pipeline_services.due_links()
        try:
            for link in links:
                PipelineInterface.enqueue_replay(link.pk, actor=actor)
        except TaskBackendUnavailable as exc:
            raise _task_error(exc) from exc
        return Response(
            ReplayEnqueueSerializer({"enqueued": len(links)}).data,
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(responses={200: LinkFailureSerializer})
    @action(
        detail=False, methods=["get"], url_path=r"links/(?P<link_id>\d+)/failure"
    )
    def link_failure(self, request, link_id):
        self.caller(request)
        link = self._link(link_id)
        return Response(
            LinkFailureSerializer(
                pipeline_services.link_failure_payload(link)
            ).data
        )

    @extend_schema(responses={200: AlertListSerializer})
    @action(detail=False, methods=["get"], url_path="alerts")
    def alerts(self, request):
        self.caller(request)
        alerts = pipeline_services.alerts(state=request.query_params.get("state"))
        return Response(
            AlertListSerializer(
                {"results": [pipeline_services.alert_payload(a) for a in alerts]}
            ).data
        )

    @extend_schema(responses={202: RerunSerializer})
    @action(
        detail=False, methods=["post"], url_path=r"links/(?P<link_id>\d+)/rerun"
    )
    def rerun(self, request, link_id):
        actor = self.caller(request)
        with transaction.atomic():
            link = self._link(link_id)
            link = type(link).objects.select_for_update().get(pk=link.pk)
            if link.pipeline_task_state in ("queued", "running"):
                return Response(
                    RerunSerializer(
                        {"link": _link_payload(link), "queued": True}
                    ).data,
                    status=status.HTTP_202_ACCEPTED,
                )
            link = pipeline_services.rerun_link_stages(link, actor=actor)
            link.pipeline_task_state = "queued"
            link.save(update_fields=["pipeline_task_state", "updated_at"])
            try:
                from django.tasks.base import TASK_MAX_PRIORITY

                PipelineInterface.enqueue_site_pipeline(
                    link.site_id,
                    actor=actor,
                    discover=False,
                    link_id=link.pk,
                    priority=TASK_MAX_PRIORITY,
                )
            except TaskBackendUnavailable as exc:
                transaction.set_rollback(True)
                raise _task_error(exc) from exc
        return Response(
            RerunSerializer({"link": _link_payload(link), "queued": True}).data,
            status=status.HTTP_202_ACCEPTED,
        )

    # Settings and observability
    @extend_schema(
        request=SettingsUpdateInputSerializer, responses={200: SettingsSerializer}
    )
    @action(detail=False, methods=["get", "put"], url_path="settings")
    def runtime_settings(self, request):
        self.caller(request)
        if request.method == "PUT":
            payload = parse_input(SettingsUpdateInputSerializer, request.data)
            from constance import config

            updated = {}
            for key, value in payload["values"].items():
                if hasattr(config, key):
                    setattr(config, key, value)
                    updated[key] = value
            return Response(SettingsSerializer({"values": updated}).data)
        return Response(SettingsSerializer({"values": _settings_snapshot()}).data)

    @extend_schema(
        request=TokenBudgetInputSerializer, responses={200: TokenBudgetSerializer}
    )
    @action(detail=False, methods=["get", "put"], url_path="llm-token-budget")
    def token_budget(self, request):
        actor = self.caller(request)
        period = "monthly"
        if request.method == "PUT":
            payload = parse_input(TokenBudgetInputSerializer, request.data)
            period = payload.get("period", "monthly")
            if payload.get("token_budget") is not None:
                pipeline_services.set_token_budget(
                    payload["token_budget"], period=period, actor=actor
                )
        else:
            period = request.query_params.get("period", "monthly")
        return Response(
            TokenBudgetSerializer(
                pipeline_services.token_budget_status(period=period)
            ).data
        )

    @extend_schema(responses={200: MetricsSerializer})
    @action(detail=False, methods=["get"], url_path="metrics")
    def metrics(self, request):
        self.caller(request)
        return Response(
            MetricsSerializer(pipeline_services.metrics_snapshot()).data
        )


def _settings_snapshot():
    from apps.core.site_config import settings_snapshot as frontend_settings_snapshot
    from apps.pipeline import constants

    values = {
        "REPLAY_PERIOD_HOURS": constants.replay_period_hours(),
        "FAILURE_RATE_THRESHOLD": constants.failure_rate_threshold(),
        "LINK_CRAWL_MAX_PAGES": constants.link_crawl_max_pages(),
        "LINK_DENY_EXTENSIONS": constants.link_deny_extensions(),
        "LINK_DENY_SEGMENTS": constants.link_deny_segments(),
        "CAPTURE_FIXED_DURATION_MS": constants.capture_fixed_duration_ms(),
        "LABELING_PROVIDER": constants.labeling_provider(),
        "LABELING_MODEL": constants.labeling_model() or "",
    }
    values.update(frontend_settings_snapshot())
    return values
