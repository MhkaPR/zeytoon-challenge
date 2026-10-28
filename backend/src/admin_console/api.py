"""DRF views for the operator console API, mounted at /api/v1/ops/."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import selectors as account_selectors
from accounts.exceptions import ApiError
from admin_console import events, serializers, services
from admin_console.models import CaptureSession, Link, Site
from admin_console.serializers import (
    ApprovalQueueSerializer,
    ConsoleErrorSerializer,
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


class AdminOnlyView(AuthenticatedView):
    """Base view requiring the operator/admin role (FR-001, FR-005)."""

    def caller(self, request):
        user = super().caller(request)
        if not user.is_admin():
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
        "has_sitemap": site.has_sitemap,
        "sitemap_url": site.sitemap_url,
        "maintenance_state": site.maintenance_state,
        "onboarded_at": site.onboarded_at.isoformat() if site.onboarded_at else None,
    }


def _link_payload(link):
    return {
        "id": link.pk,
        "url": link.url,
        "source": link.source,
        "review_state": link.review_state,
        "pipeline_stage": link.pipeline_stage,
        "failure_rate": link.failure_rate,
        "current_trace_id": link.current_trace_id,
    }


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


# ---------------------------------------------------------------------------
# US1 — approval queue (FR-001..FR-006)
# ---------------------------------------------------------------------------


class ApprovalQueueView(AdminOnlyView):
    @extend_schema(responses={200: ApprovalQueueSerializer})
    def get(self, request):
        actor = self.caller(request)
        results = services.approval_queue()
        events.approval_queue_read(len(results), actor=actor)
        return Response({"results": results, "count": len(results)})


class VerificationDecisionView(AdminOnlyView):
    @extend_schema(
        request=VerificationDecisionInputSerializer,
        responses={201: dict, 400: ConsoleErrorSerializer, 403: ConsoleErrorSerializer},
    )
    def post(self, request, company_id):
        actor = self.caller(request)
        payload = parse_input(VerificationDecisionInputSerializer, request.data)
        company, decision, site = services.record_decision(
            company_id,
            actor,
            payload["outcome"],
            note=payload.get("note", ""),
        )
        return Response(
            {
                "company": {
                    "id": company.pk,
                    "verification_status": company.verification_status,
                    "verified": company.is_verified,
                },
                "decision": {
                    "outcome": decision.outcome,
                    "actor_id": decision.actor_id,
                    "decided_at": decision.decided_at.isoformat(),
                    "note": decision.note,
                },
                "site": _site_payload(site) if site is not None else None,
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# US2 — site onboarding and link review (FR-007..FR-011)
# ---------------------------------------------------------------------------


class SiteCreateView(AdminOnlyView):
    @extend_schema(operation_id="ops_sites_list", responses={200: dict})
    def get(self, request):
        self.caller(request)
        results = []
        for site in Site.objects.select_related("company").all():
            payload = _site_payload(site)
            payload["links_count"] = site.links.count()
            results.append(payload)
        return Response({"results": results, "count": len(results)})

    @extend_schema(request=serializers.SiteCreateInput, responses={201: dict})
    def post(self, request):
        actor = self.caller(request)
        payload = parse_input(serializers.SiteCreateInput, request.data)
        site = services.onboard_site(payload.company_id, actor)
        return Response(
            {"site": _site_payload(site)}, status=status.HTTP_201_CREATED
        )


class SiteDetailView(AdminOnlyView):
    @extend_schema(operation_id="ops_site_detail", responses={200: dict})
    def get(self, request, site_id):
        site = get_site_or_error(site_id)
        links = [_link_payload(link) for link in site.links.all()]
        return Response({"site": _site_payload(site), "links": links})


class DiscoverLinksView(AdminOnlyView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, site_id):
        actor = self.caller(request)
        site = get_site_or_error(site_id)
        result = services.discover_and_store_links(site, actor)
        return Response(result)


class SiteLinksView(AdminOnlyView):
    @extend_schema(responses={200: dict})
    def get(self, request, site_id):
        site = get_site_or_error(site_id)
        links = [_link_payload(link) for link in site.links.all()]
        return Response({"site_id": site.pk, "links": links})

    @extend_schema(request=serializers.ManualLinksInput, responses={201: dict})
    def post(self, request, site_id):
        actor = self.caller(request)
        site = get_site_or_error(site_id)
        payload = parse_input(serializers.ManualLinksInput, request.data)
        result = services.add_links_manually(site, payload.urls, actor)
        return Response(result, status=status.HTTP_201_CREATED)


class LinkReviewView(AdminOnlyView):
    @extend_schema(request=serializers.LinkReviewInput, responses={200: dict})
    def post(self, request, site_id):
        actor = self.caller(request)
        site = get_site_or_error(site_id)
        payload = parse_input(serializers.LinkReviewInput, request.data)
        result = services.review_links(
            site, payload.keep_ids, payload.remove_ids, actor
        )
        return Response(result)


# ---------------------------------------------------------------------------
# US3 — operator-driven capture (FR-012..FR-017)
# ---------------------------------------------------------------------------


def _capture_payload(session):
    return {
        "id": session.pk,
        "link_id": session.link_id,
        "mode": session.mode,
        "state": session.state,
        "local_path": session.local_path,
        "duration_ms": session.duration_ms,
        "error": session.error,
        "trace_id": session.trace_id,
    }


class CaptureStartView(AdminOnlyView):
    @extend_schema(request=serializers.CaptureStartInput, responses={201: dict})
    def post(self, request, link_id):
        actor = self.caller(request)
        link = get_link_or_error(link_id)
        payload = parse_input(serializers.CaptureStartInput, request.data)
        session, _ = services.start_capture(
            link, actor, mode=payload.mode, duration_ms=payload.duration_ms
        )
        return Response(
            {"capture": _capture_payload(session)}, status=status.HTTP_201_CREATED
        )


class TraceUploadView(AdminOnlyView):
    @extend_schema(request=None, responses={201: dict})
    def post(self, request, capture_session_id):
        actor = self.caller(request)
        session = CaptureSession.objects.filter(pk=capture_session_id).first()
        if session is None:
            raise ApiError("not_found", "Capture session not found.", http_status=404)
        upload = request.FILES.get("file")
        if upload is not None:
            source = upload
        elif request.data.get("local_path"):
            source = request.data["local_path"]
        else:
            raise ApiError(
                "invalid_field",
                "Provide a trace file or a local_path.",
                fields={"fields": ["file", "local_path"]},
            )
        trace = services.store_trace(session, source, actor)
        return Response(
            {
                "trace": {
                    "id": trace.pk,
                    "link_id": trace.link_id,
                    "captured_at": trace.captured_at.isoformat(),
                    "captured_by": trace.captured_by_id,
                    "is_valid_trace": trace.is_valid_trace,
                },
                "capture": _capture_payload(session),
            },
            status=status.HTTP_201_CREATED,
        )


class CaptureFailView(AdminOnlyView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, capture_session_id):
        self.caller(request)
        session = CaptureSession.objects.filter(pk=capture_session_id).first()
        if session is None:
            raise ApiError("not_found", "Capture session not found.", http_status=404)
        services.fail_capture(session, request.data.get("error", "operator failed"))
        return Response({"capture": _capture_payload(session)})


# ---------------------------------------------------------------------------
# US4 — table extraction (FR-018..FR-020)
# ---------------------------------------------------------------------------


class ExtractionView(AdminOnlyView):
    @extend_schema(request=None, responses={201: dict, 409: ConsoleErrorSerializer})
    def post(self, request, link_id):
        self.caller(request)
        link = get_link_or_error(link_id)
        if link.current_trace is None:
            raise ApiError(
                "trace_required",
                "A stored trace is required before extraction.",
                http_status=409,
            )
        from admin_console.tasks import run_extraction_task

        task_result = run_extraction_task.enqueue(link.pk)
        if not task_result.is_finished:
            # A queued (non-immediate) backend runs the task elsewhere.
            return Response(
                {"link_id": link.pk, "queued": True},
                status=status.HTTP_202_ACCEPTED,
            )
        if task_result.errors:
            detail = task_result.errors[0].traceback or "extraction failed"
            raise ApiError(
                "extraction_failed",
                "Table extraction failed.",
                fields={"detail": str(detail)[-300:]},
            )
        result = task_result.return_value
        return Response(result, status=status.HTTP_201_CREATED)


class LinkTablesView(AdminOnlyView):
    @extend_schema(responses={200: dict})
    def get(self, request, link_id):
        self.caller(request)
        link = get_link_or_error(link_id)
        return Response(
            {
                "link_id": link.pk,
                "url": link.url,
                "pipeline_stage": link.pipeline_stage,
                "current_trace_id": link.current_trace_id,
                "tables": services.tables_payload(link),
            }
        )


# ---------------------------------------------------------------------------
# US5 — labeling, settings, and cost ceiling (FR-021..FR-024, FR-043)
# ---------------------------------------------------------------------------


class LabelingView(AdminOnlyView):
    @extend_schema(request=None, responses={200: dict, 403: dict, 409: dict})
    def post(self, request, link_id):
        actor = self.caller(request)
        link = get_link_or_error(link_id)
        # Gate synchronously so domain errors surface as their contract codes.
        services.assert_labeling_allowed(link)
        from admin_console.tasks import run_labeling_task

        task_result = run_labeling_task.enqueue(link.pk, actor.pk)
        if not task_result.is_finished:
            return Response({"queued": True}, status=status.HTTP_202_ACCEPTED)
        if task_result.errors:
            raise ApiError(
                "labeling_failed",
                "Labeling failed.",
                fields={"detail": str(task_result.errors[0].traceback)[-300:]},
            )
        return Response(task_result.return_value)


TUNABLE_FIELDS = (
    "REPLAY_PERIOD_HOURS",
    "REPLAY_BATCH_SIZE",
    "FAILURE_RATE_THRESHOLD",
    "FAILURE_RATE_WINDOW_RUNS",
    "LABELING_ENABLED",
    "LABELING_PROVIDER",
    "LABELING_MODEL",
    "LABELING_LANGUAGE",
    "LABELING_BATCH_SIZE",
    "SITEMAP_FETCH_TIMEOUT_SECONDS",
    "SITEMAP_MAX_INDEX_DEPTH",
    "LINK_DISCOVERY_MAX_LINKS",
    "CLEANING_RULES",
    "CAPTURE_MODES_ALLOWED",
    "PUBLISH_AUTO_THRESHOLD",
)


class SettingsView(AdminOnlyView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        self.caller(request)
        from constance import config

        return Response({field: getattr(config, field) for field in TUNABLE_FIELDS})

    @extend_schema(request=serializers.SettingsUpdateInput, responses={200: dict})
    def put(self, request):
        self.caller(request)
        from constance import config

        payload = parse_input(serializers.SettingsUpdateInput, request.data)
        for key, value in (payload.values or {}).items():
            if key not in TUNABLE_FIELDS:
                raise ApiError(
                    "invalid_field",
                    "Unknown tunable.",
                    fields={"fields": [key]},
                )
            setattr(config, key, value)
        return Response({field: getattr(config, field) for field in TUNABLE_FIELDS})


class LlmCostCeilingView(AdminOnlyView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        self.caller(request)
        return Response(services.llm_ceiling_status())

    @extend_schema(request=serializers.LlmCostCeilingInput, responses={200: dict})
    def put(self, request):
        actor = self.caller(request)
        payload = parse_input(serializers.LlmCostCeilingInput, request.data)
        services.set_llm_ceiling(
            payload.ceiling_amount, period=payload.period, actor=actor
        )
        return Response(services.llm_ceiling_status())


# ---------------------------------------------------------------------------
# US6 — mapping workspace and the extraction recipe (FR-025..FR-031)
# ---------------------------------------------------------------------------


class PlanSchemaView(AdminOnlyView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        self.caller(request)
        from admin_console.plan_schema import PLAN_SCHEMA

        return Response(
            {
                "plan_types": [
                    {
                        "key": plan.key,
                        "label": plan.label,
                        "fields": [
                            {
                                "key": f.key,
                                "label": f.label,
                                "kind": f.kind,
                                "required": f.required,
                                "unit_family": f.unit_family,
                                "values": list(f.values),
                            }
                            for f in plan.fields
                        ],
                    }
                    for plan in PLAN_SCHEMA.values()
                ]
            }
        )


class RecipeView(AdminOnlyView):
    @extend_schema(responses={200: dict})
    def get(self, request, link_id):
        self.caller(request)
        link = get_link_or_error(link_id)
        recipe = services.get_current_recipe(link)
        return Response(
            {
                "link_id": link.pk,
                "pipeline_stage": link.pipeline_stage,
                "recipe": services.recipe_payload(recipe),
                "tables": services.tables_payload(link),
            }
        )

    @extend_schema(request=serializers.RecipeSaveInput, responses={200: dict, 409: dict})
    def put(self, request, link_id):
        actor = self.caller(request)
        link = get_link_or_error(link_id)
        payload = parse_input(serializers.RecipeSaveInput, request.data)
        recipe, unconnected = services.save_recipe(
            link,
            payload.plan_type,
            [b.model_dump() for b in payload.bindings],
            actor=actor,
        )
        link.refresh_from_db()
        if not recipe.is_complete:
            raise ApiError(
                "recipe_incomplete",
                "Required schema fields are unconnected.",
                http_status=409,
                fields={"unconnected": unconnected},
            )
        return Response(
            {
                "recipe": services.recipe_payload(recipe),
                "link": {"pipeline_stage": link.pipeline_stage},
            }
        )


# ---------------------------------------------------------------------------
# US7 — cleaning and publishing (FR-032..FR-036)
# ---------------------------------------------------------------------------


class CleaningView(AdminOnlyView):
    @extend_schema(request=None, responses={200: dict, 409: dict})
    def post(self, request, link_id):
        actor = self.caller(request)
        link = get_link_or_error(link_id)
        result = services.clean_link_data(link, actor=actor)
        return Response(result)


class PublishView(AdminOnlyView):
    @extend_schema(request=None, responses={200: dict, 409: dict})
    def post(self, request, link_id):
        actor = self.caller(request)
        link = get_link_or_error(link_id)
        result = services.publish_link_data(link, actor=actor)
        return Response(result)


# ---------------------------------------------------------------------------
# US8 — replay runs, failure state, alerts, re-run, recipients (FR-037..FR-042)
# ---------------------------------------------------------------------------


class ReplayRunListView(AdminOnlyView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        self.caller(request)
        link_id = request.query_params.get("link_id")
        runs = services.replay_runs(link_id=link_id)
        return Response(
            {
                "results": [services.replay_run_payload(run) for run in runs],
                "count": len(runs),
            }
        )


class ReplayRunCreateView(AdminOnlyView):
    @extend_schema(request=serializers.ReplayRunInput, responses={201: dict, 409: dict})
    def post(self, request):
        self.caller(request)
        payload = parse_input(serializers.ReplayRunInput, request.data)
        if payload.site_id is not None:
            links = services.due_links_for_site(payload.site_id)
        elif payload.link_ids:
            links = list(Link.objects.filter(pk__in=payload.link_ids))
        else:
            links = services.due_links()
        results = []
        for link in links:
            from admin_console.replay import execute_replay_run

            results.append(execute_replay_run(link))
        return Response({"results": results, "count": len(results)}, status=201)


class LinkFailureView(AdminOnlyView):
    @extend_schema(responses={200: dict})
    def get(self, request, link_id):
        self.caller(request)
        link = get_link_or_error(link_id)
        return Response(services.link_failure_payload(link))


class AlertListView(AdminOnlyView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        self.caller(request)
        state = request.query_params.get("state")
        alerts = services.alerts(state=state)
        return Response(
            {
                "results": [services.alert_payload(a) for a in alerts],
                "count": len(alerts),
            }
        )


class LinkRerunView(AdminOnlyView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, link_id):
        actor = self.caller(request)
        link = get_link_or_error(link_id)
        return Response(services.rerun_link_stages(link, actor=actor))


class MetricsView(AdminOnlyView):
    """Operational metrics for the console (FR-045, Principle VII)."""

    @extend_schema(responses={200: dict})
    def get(self, request):
        self.caller(request)
        return Response(services.metrics_snapshot())
