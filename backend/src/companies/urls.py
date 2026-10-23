"""Company routes, mounted under /api/v1/companies/.

The panel surface, verification decisions, plan eligibility, credit, and crawl all live in
this module — there is no separate ``panel`` app.
"""

from django.urls import path

from companies import api

app_name = "companies"

urlpatterns = [
    # Registration (US1)
    path("", api.CompanyListCreateView.as_view(), name="company-list-create"),
    path("<int:pk>", api.CompanyDetailView.as_view(), name="company-detail"),
    path(
        "<int:pk>/steps/<str:step_key>/abandon",
        api.StepAbandonView.as_view(),
        name="step-abandon",
    ),
    # Panel (US2)
    path("panel-switcher", api.PanelSwitcherView.as_view(), name="panel-switcher"),
    path("<int:pk>/panel-entry", api.PanelEntryView.as_view(), name="panel-entry"),
    path("<int:pk>/panel", api.PanelFullView.as_view(), name="panel-full"),
    # Verification decision (US3)
    path(
        "<int:pk>/verification-decisions",
        api.VerificationDecisionView.as_view(),
        name="verification-decision",
    ),
    # Plan eligibility, credit, crawl (US4)
    path("<int:pk>/plan-eligibility", api.PlanEligibilityView.as_view(), name="plan-eligibility"),
    path("<int:pk>/credit", api.CompanyCreditView.as_view(), name="company-credit"),
    path(
        "<int:pk>/credit/movements",
        api.CreditMovementView.as_view(),
        name="credit-movement",
    ),
    path("<int:pk>/crawl", api.CrawlView.as_view(), name="company-crawl"),
    # Ownership transfer refusal (US5)
    path(
        "<int:pk>/transfer-ownership",
        api.OwnershipTransferView.as_view(),
        name="transfer-ownership",
    ),
]
