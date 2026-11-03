"""DRF views for company registration, the panel surface, verification, and link submission.

All of this feature's endpoints live in the ``companies`` module (there is no separate
``panel`` app). Authentication reuses the ``accounts`` JWT: the caller is resolved from the
Bearer token, and every company-scoped request is limited to companies the caller owns.
"""

from django.utils import timezone
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response


from accounts import selectors as account_selectors
from accounts.exceptions import ApiError
from companies import constants, selectors, services
from companies.models import Company
from companies.serializers import (
    CompanyInformationInput,
    CompanyInformationSerializer,
    CompanySerializer,
    ErrorSerializer,
    PlanEligibilitySerializer,
    CompanyDetailSerializer,
    PanelEntrySerializer,
    PanelSwitcherSerializer,
    VerificationDecisionResponseSerializer,
    StepProgressSerializer,
    VerificationDecisionInputSerializer,
    parse_input,
)


def _company_payload(company):
    return {
        "id": company.pk,
        "domain": company.domain,
        "company_name": company.company_name,
        "representative_name": company.representative_name,
        "phone_number": company.phone_number,
        "internal_number": company.internal_number,
        "verification_status": company.verification_status,
        "is_archived": company.is_archived,
        "unverified": company.is_unverified,
    }


class AuthenticatedView(GenericAPIView):
    """Base view resolving the JWT caller and refusing guests."""

    def caller(self, request):
        user = account_selectors.user_from_request(request)
        if user is None:
            raise ApiError(
                "not_authenticated", "Authentication is required.", http_status=401
            )
        return user


class AdminOnlyView(AuthenticatedView):
    """Base view requiring the ``admin`` role (FR-012)."""

    def caller(self, request):
        user = super().caller(request)
        if not user.is_admin():
            raise ApiError(
                "not_permitted", "This action is restricted.", http_status=403
            )
        return user


# ---------------------------------------------------------------------------
# Registration (US1)
# ---------------------------------------------------------------------------


class CompanyListCreateView(AuthenticatedView):
    @extend_schema(
        request=CompanyInformationSerializer, responses={201: CompanySerializer}
    )
    def post(self, request):
        user = self.caller(request)
        payload = parse_input(CompanyInformationInput, request.data)
        company = services.register_company(user, payload.model_dump())
        body = {
            "company": _company_payload(company),
            "step_progress": selectors.step_progress_payload(company),
        }
        return Response(body, status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: CompanySerializer(many=True)})
    def get(self, request):
        user = self.caller(request)
        companies = [
            _company_payload(company)
            for company in selectors.list_owned_companies(user)
        ]
        return Response({"companies": companies})


class CompanyDetailView(AuthenticatedView):
    @extend_schema(responses={200: CompanyDetailSerializer})
    def get(self, request, pk):
        user = self.caller(request)
        company = selectors.owned_company_or_error(user, pk)
        body = {
            "company": _company_payload(company),
            "step_progress": selectors.step_progress_payload(company),
            "current_step": selectors.current_step(company),
        }
        return Response(body)


class StepAbandonView(AuthenticatedView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, pk, step_key):
        user = self.caller(request)
        company = selectors.owned_company_or_error(user, pk)
        services.abandon_step(user, company, step_key)
        return Response(
            {
                "step_key": step_key,
                "resume_at": selectors.current_step(company),
                "drafts_cleared": [step_key],
            }
        )


# ---------------------------------------------------------------------------
# Panel entry, switching, continue view (US2)
# ---------------------------------------------------------------------------


class PanelSwitcherView(AuthenticatedView):
    @extend_schema(responses={200: PanelSwitcherSerializer})
    def get(self, request):
        user = self.caller(request)
        companies = list(selectors.list_owned_companies(user))
        if not companies:
            return Response(
                {
                    "companies": [],
                    "empty_state": True,
                    "message": constants.empty_state_message(),
                }
            )
        return Response(
            {
                "companies": [
                    {
                        "id": company.pk,
                        "company_name": company.company_name,
                        "verification_status": company.verification_status,
                        "unverified": company.is_unverified,
                    }
                    for company in companies
                ],
                "empty_state": False,
            }
        )


class PanelEntryView(AuthenticatedView):
    @extend_schema(responses={200: PanelEntrySerializer})
    def get(self, request, pk):
        user = self.caller(request)
        company = selectors.owned_company_or_error(user, pk)
        if company.is_verified:
            return Response(
                {"view": "full_panel", "company": _company_payload(company)}
            )
        return Response(
            {
                "view": "continue_registration",
                "company": _company_payload(company),
                "step_progress": selectors.step_progress_payload(company),
                "current_step": selectors.current_step(company),
                "verification_status": company.verification_status,
            }
        )


class PanelFullView(AuthenticatedView):
    @extend_schema(responses={200: CompanyDetailSerializer, 303: None})
    def get(self, request, pk):
        user = self.caller(request)
        company = selectors.owned_company_or_error(user, pk)
        if not company.is_verified:
            # Redirect to the continue view; the full panel never renders (FR-027, SC-003).
            return Response(
                status=status.HTTP_303_SEE_OTHER,
                headers={"Location": f"/api/v1/companies/{company.pk}/panel-entry"},
            )
        return Response(
            {
                "company": _company_payload(company),
                "plan_eligibility": services.can_manage_plans(company),
            }
        )


# ---------------------------------------------------------------------------
# Verification decision (US3)
# ---------------------------------------------------------------------------


class VerificationDecisionView(AdminOnlyView):
    @extend_schema(
        request=VerificationDecisionInputSerializer,
        responses={201: VerificationDecisionResponseSerializer},
    )
    def post(self, request, pk):
        actor = self.caller(request)
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
        body = {
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
        code = status.HTTP_201_CREATED if company.is_verified else status.HTTP_200_OK
        return Response(body, status=code)


# ---------------------------------------------------------------------------
# Plan eligibility
# ---------------------------------------------------------------------------


class PlanEligibilityView(AuthenticatedView):
    @extend_schema(responses={200: PlanEligibilitySerializer})
    def get(self, request, pk):
        user = self.caller(request)
        company = selectors.owned_company_or_error(user, pk)
        return Response(services.can_manage_plans(company))


class CompanyLinksView(AuthenticatedView):
    """Let a company submit additional pages from its own domain for crawling."""

    def post(self, request, pk):
        from admin_console import discovery, services as crawl_services
        from admin_console.models import Site
        from admin_console.serializers import ManualLinksInput

        user = self.caller(request)
        company = selectors.owned_company_or_error(user, pk)
        payload = parse_input(ManualLinksInput, request.data)
        site, _ = Site.objects.get_or_create(
            company=company,
            defaults={"domain": company.domain, "onboarded_at": timezone.now()},
        )
        host = company.domain.lower().removeprefix("www.")
        urls = discovery.apply_link_policy(payload.urls, host=host)
        links = crawl_services.add_links_manually(site, urls, actor=user)
        if links:
            from admin_console.tasks import run_site_pipeline_task

            transaction.on_commit(
                lambda: run_site_pipeline_task.enqueue(site.pk, discover=False)
            )
        return Response(
            {"links": [{"id": link.pk, "url": link.url} for link in links]},
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Ownership transfer refusal (US5)
# ---------------------------------------------------------------------------


class OwnershipTransferView(AuthenticatedView):
    @extend_schema(request=None, responses={409: ErrorSerializer})
    def post(self, request, pk):
        user = self.caller(request)
        company = selectors.owned_company_or_error(user, pk)
        services.refuse_ownership_transfer(company, actor=user)
