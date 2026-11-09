"""DRF views for company registration, the panel surface, verification, and link submission.

All of this feature's endpoints live in the ``companies`` module (there is no separate
``panel`` app). Authentication reuses the ``accounts`` JWT: the caller is resolved from the
Bearer token, and every company-scoped request is limited to companies the caller owns.
"""

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts import selectors as account_selectors
from apps.accounts.exceptions import ApiError
from apps.companies import constants, selectors, services
from apps.companies.models import Company
from apps.companies.serializers import (
    CompanyDetailSerializer,
    CompanyInformationSerializer,
    CompanyCreditSerializer,
    CompanyLinksSerializer,
    CreditMovementInputSerializer,
    CrawlToggleInputSerializer,
    CrawlToggleResponseSerializer,
    CompanyListSerializer,
    CompanyRegistrationSerializer,
    CompanySerializer,
    ErrorSerializer,
    PanelEntrySerializer,
    PanelSwitcherSerializer,
    PlanEligibilitySerializer,
    StepAbandonSerializer,
    StepProgressSerializer,
    VerificationDecisionInputSerializer,
    VerificationDecisionResponseSerializer,
    parse_input,
)


class AuthenticatedViewSet(GenericViewSet):
    """Base viewset resolving the JWT caller and refusing guests."""

    def caller(self, request):
        user = account_selectors.user_from_request(request)
        if user is None:
            raise ApiError(
                "not_authenticated", "Authentication is required.", http_status=401
            )
        return user


class CompanyViewSet(
    ListModelMixin, CreateModelMixin, RetrieveModelMixin, AuthenticatedViewSet
):
    """Company registration, panel entry, verification, and link submission."""

    queryset = Company.objects.all()

    def get_queryset(self):
        user = self.caller(self.request)
        return selectors.list_owned_companies(user)

    def _company(self, pk):
        user = self.caller(self.request)
        return selectors.owned_company_or_error(user, pk)

    # Registration (US1)

    @extend_schema(
        request=CompanyInformationSerializer, responses={201: CompanyRegistrationSerializer}
    )
    def create(self, request, *args, **kwargs):
        user = self.caller(request)
        payload = parse_input(CompanyInformationSerializer, request.data)
        company = services.register_company(user, payload)
        body = CompanyRegistrationSerializer(
            {
                "company": company,
                "step_progress": selectors.step_progress(company),
            }
        ).data
        return Response(body, status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: CompanyListSerializer})
    def list(self, request, *args, **kwargs):
        companies = selectors.list_owned_companies(self.caller(request))
        return Response(CompanyListSerializer({"companies": companies}).data)

    @extend_schema(responses={200: CompanyDetailSerializer})
    def retrieve(self, request, pk=None):
        company = self._company(pk)
        return Response(
            CompanyDetailSerializer(
                {
                    "company": company,
                    "step_progress": selectors.step_progress(company),
                    "current_step": selectors.current_step(company),
                }
            ).data
        )

    @extend_schema(request=None, responses={200: StepAbandonSerializer})
    @action(
        detail=True,
        methods=["post"],
        url_path="steps/(?P<step_key>[^/.]+)/abandon",
    )
    def abandon_step(self, request, pk=None, step_key=None):
        user = self.caller(request)
        company = self._company(pk)
        services.abandon_step(user, company, step_key)
        return Response(
            StepAbandonSerializer(
                {
                    "step_key": step_key,
                    "resume_at": selectors.current_step(company),
                    "drafts_cleared": [step_key],
                }
            ).data
        )

    # Panel entry, switching, continue view (US2)

    @extend_schema(responses={200: PanelSwitcherSerializer})
    @action(detail=False, methods=["get"], url_path="panel-switcher")
    def panel_switcher(self, request):
        companies = list(selectors.list_owned_companies(self.caller(request)))
        if not companies:
            return Response(
                PanelSwitcherSerializer(
                    {
                        "companies": [],
                        "empty_state": True,
                        "message": constants.empty_state_message(),
                    }
                ).data
            )
        return Response(
            PanelSwitcherSerializer(
                {"companies": companies, "empty_state": False}
            ).data
        )

    @extend_schema(responses={200: PanelEntrySerializer})
    @action(detail=True, methods=["get"], url_path="panel-entry")
    def panel_entry(self, request, pk=None):
        company = self._company(pk)
        if company.is_verified:
            return Response(
                PanelEntrySerializer(
                    {"view": "full_panel", "company": company}
                ).data
            )
        return Response(
            PanelEntrySerializer(
                {
                    "view": "continue_registration",
                    "company": company,
                    "step_progress": selectors.step_progress(company),
                    "current_step": selectors.current_step(company),
                    "verification_status": company.verification_status,
                }
            ).data
        )

    @extend_schema(responses={200: CompanyDetailSerializer, 303: None})
    @action(detail=True, methods=["get"], url_path="panel")
    def panel(self, request, pk=None):
        company = self._company(pk)
        if not company.is_verified:
            # Redirect to the continue view; the full panel never renders (FR-027, SC-003).
            return Response(
                status=status.HTTP_303_SEE_OTHER,
                headers={"Location": f"/api/v1/companies/{company.pk}/panel-entry"},
            )
        return Response(
            CompanyDetailSerializer(
                {
                    "company": company,
                    "step_progress": selectors.step_progress(company),
                    "current_step": selectors.current_step(company),
                    "plan_eligibility": services.can_manage_plans(company),
                }
            ).data
        )

    # Verification decision (US3)

    @extend_schema(
        request=VerificationDecisionInputSerializer,
        responses={201: VerificationDecisionResponseSerializer},
    )
    @action(detail=True, methods=["post"], url_path="verification-decisions")
    def verification_decision(self, request, pk=None):
        actor = account_selectors.user_from_request(request)
        if actor is None:
            raise ApiError(
                "not_authenticated", "Authentication is required.", http_status=401
            )
        if not actor.is_admin():
            raise ApiError(
                "not_permitted", "This action is restricted.", http_status=403
            )
        company = Company.objects.filter(pk=pk).first()
        if company is None:
            raise ApiError("not_found", "Company not found.", http_status=404)
        if company.owner_id == actor.pk:
            # The owner can never decide their own verification (FR-012).
            raise ApiError(
                "not_permitted",
                "An owner cannot decide their own verification.",
                http_status=403,
            )
        payload = parse_input(VerificationDecisionInputSerializer, request.data)
        decision = services.record_verification_decision(
            company, actor, payload["outcome"], note=payload.get("note", "")
        )
        body = VerificationDecisionResponseSerializer(
            {
                "company_id": company.pk,
                "verification_status": company.verification_status,
                "current_step": selectors.current_step(company),
                "decision": {
                    "outcome": decision.outcome,
                    "actor_id": decision.actor_id,
                    "decided_at": decision.decided_at.isoformat(),
                    "note": decision.note,
                },
            }
        ).data
        code = status.HTTP_201_CREATED if company.is_verified else status.HTTP_200_OK
        return Response(body, status=code)

    # Plan eligibility

    @extend_schema(responses={200: PlanEligibilitySerializer})
    @action(detail=True, methods=["get"], url_path="plan-eligibility")
    def plan_eligibility(self, request, pk=None):
        company = self._company(pk)
        return Response(PlanEligibilitySerializer(services.can_manage_plans(company)).data)

    @extend_schema(
        request=CreditMovementInputSerializer,
        responses={201: CompanyCreditSerializer},
    )
    @action(detail=True, methods=["post"], url_path="credit/movements")
    def credit_movements(self, request, pk=None):
        company = self._company(pk)
        payload = parse_input(CreditMovementInputSerializer, request.data)
        services.record_credit_movement(
            company,
            payload["direction"],
            payload["amount"],
            payload["reason"],
            reference=payload.get("reference", ""),
            actor=self.caller(request),
        )
        return Response(
            CompanyCreditSerializer(
                {
                    "current_credit": selectors.credit_projection(company),
                    "entries": [
                        {
                            "id": entry.pk,
                            "direction": entry.direction,
                            "amount": entry.amount,
                            "reason": entry.reason,
                            "reference": entry.reference,
                        }
                        for entry in company.credit_entries.all()
                    ],
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=CrawlToggleInputSerializer,
        responses={200: CrawlToggleResponseSerializer},
    )
    @action(detail=True, methods=["post"], url_path="crawl")
    def crawl(self, request, pk=None):
        company = self._company(pk)
        payload = parse_input(CrawlToggleInputSerializer, request.data)
        services.set_crawl_enabled(company, payload["enabled"])
        return Response(
            CrawlToggleResponseSerializer(
                {"crawl_enabled": company.crawl_enabled, "credit_unchanged": True}
            ).data
        )

    @extend_schema(responses={200: CompanyCreditSerializer})
    @action(detail=True, methods=["get"], url_path="credit")
    def credit(self, request, pk=None):
        company = self._company(pk)
        entries = company.credit_entries.all()
        return Response(
            CompanyCreditSerializer(
                {
                    "current_credit": selectors.credit_projection(company),
                    "entries": [
                        {
                            "id": entry.pk,
                            "direction": entry.direction,
                            "amount": entry.amount,
                            "reason": entry.reason,
                            "reference": entry.reference,
                        }
                        for entry in entries
                    ],
                }
            ).data
        )

    @extend_schema(responses={201: CompanyLinksSerializer})
    @action(detail=True, methods=["post"], url_path="links")
    def links(self, request, pk=None):
        """Let a company submit additional pages from its own domain for crawling."""
        from apps.pipeline import discovery
        from apps.pipeline.services.v1 import pipeline as crawl_services
        from apps.pipeline.models import Site
        from apps.admin_console.serializers import ManualLinksInput

        user = self.caller(request)
        company = self._company(pk)
        payload = parse_input(ManualLinksInput, request.data)
        site, _ = Site.objects.get_or_create(
            company=company,
            defaults={"domain": company.domain, "onboarded_at": timezone.now()},
        )
        host = company.domain.lower().removeprefix("www.")
        urls = discovery.apply_link_policy(payload.urls, host=host)
        links = crawl_services.add_links_manually(site, urls, actor=user)
        if links:
            from apps.pipeline.tasks import run_site_pipeline_task

            transaction.on_commit(
                lambda: run_site_pipeline_task.enqueue(site.pk, discover=False)
            )
        return Response(
            CompanyLinksSerializer({"links": list(links)}).data,
            status=status.HTTP_201_CREATED,
        )

    # Ownership transfer refusal (US5)

    @extend_schema(request=None, responses={409: ErrorSerializer})
    @action(detail=True, methods=["post"], url_path="transfer-ownership")
    def transfer_ownership(self, request, pk=None):
        user = self.caller(request)
        company = self._company(pk)
        services.refuse_ownership_transfer(company, actor=user)
        return Response(status=status.HTTP_409_CONFLICT)
