"""Operator console routes, mounted under /api/v1/ops/."""

from django.urls import path

from admin_console import api

app_name = "admin_console"

urlpatterns = [
    # US1 — approval queue (FR-001..FR-006)
    path("approvals", api.ApprovalQueueView.as_view(), name="approval-queue"),
    path(
        "companies/<int:company_id>/verification-decisions",
        api.VerificationDecisionView.as_view(),
        name="verification-decision",
    ),
    # US2 — site onboarding and link review (FR-007..FR-011)
    path("sites", api.SiteCreateView.as_view(), name="site-create"),
    path("sites/<int:site_id>", api.SiteDetailView.as_view(), name="site-detail"),
    path(
        "sites/<int:site_id>/discover-links",
        api.DiscoverLinksView.as_view(),
        name="site-discover-links",
    ),
    path(
        "sites/<int:site_id>/links",
        api.SiteLinksView.as_view(),
        name="site-links",
    ),
    path(
        "sites/<int:site_id>/links/review",
        api.LinkReviewView.as_view(),
        name="site-links-review",
    ),
    # US3 — operator-driven capture (FR-012..FR-017)
    path(
        "links/<int:link_id>/captures",
        api.CaptureStartView.as_view(),
        name="capture-start",
    ),
    path(
        "captures/active",
        api.ActiveCaptureView.as_view(),
        name="capture-active",
    ),
    path("domtrack/health", api.DomtrackHealthView.as_view(), name="domtrack-health"),
    path(
        "captures/<int:capture_session_id>/trace",
        api.TraceUploadView.as_view(),
        name="capture-trace",
    ),
    path(
        "captures/<int:capture_session_id>/fail",
        api.CaptureFailView.as_view(),
        name="capture-fail",
    ),
    # US4 — table extraction (FR-018..FR-020)
    path(
        "links/<int:link_id>/extractions",
        api.ExtractionView.as_view(),
        name="link-extractions",
    ),
    path(
        "links/<int:link_id>/tables",
        api.LinkTablesView.as_view(),
        name="link-tables",
    ),
    # US5 — labeling, settings, and cost ceiling (FR-021..FR-024, FR-043)
    path(
        "links/<int:link_id>/labeling",
        api.LabelingView.as_view(),
        name="link-labeling",
    ),
    path("settings", api.SettingsView.as_view(), name="settings"),
    path(
        "llm-cost-ceiling",
        api.LlmCostCeilingView.as_view(),
        name="llm-cost-ceiling",
    ),
    # US6 — mapping workspace and the extraction recipe (FR-025..FR-031)
    path("plan-schema", api.PlanSchemaView.as_view(), name="plan-schema"),
    path("links/<int:link_id>/recipe", api.RecipeView.as_view(), name="link-recipe"),
    # US7 — cleaning and publishing (FR-032..FR-036)
    path(
        "links/<int:link_id>/cleaning",
        api.CleaningView.as_view(),
        name="link-cleaning",
    ),
    path(
        "links/<int:link_id>/publish",
        api.PublishView.as_view(),
        name="link-publish",
    ),
    # US8 — replay runs, failure state, alerts, re-run (FR-037..FR-042)
    path("replay-runs", api.ReplayRunListView.as_view(), name="replay-runs"),
    path(
        "replay-runs/create",
        api.ReplayRunCreateView.as_view(),
        name="replay-runs-create",
    ),
    path(
        "links/<int:link_id>/failure",
        api.LinkFailureView.as_view(),
        name="link-failure",
    ),
    path(
        "links/<int:link_id>/rerun",
        api.LinkRerunView.as_view(),
        name="link-rerun",
    ),
    path("alerts", api.AlertListView.as_view(), name="alerts"),
    # Phase 11 — operational metrics (FR-045)
    path("metrics", api.MetricsView.as_view(), name="metrics"),
]
