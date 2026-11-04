"""Operator console routes, mounted under /api/v1/ops/."""

from django.urls import path

from apps.admin_console import api

app_name = "admin_console"

urlpatterns = [
    # US1 — approval queue (FR-001..FR-006)
    path("approvals", api.ApprovalQueueView.as_view(), name="approval-queue"),
    path(
        "companies/<int:company_id>/verification-decisions",
        api.VerificationDecisionView.as_view(),
        name="verification-decision",
    ),
    # US2 — automated link discovery (FR-007..FR-011)
    path("sites", api.SiteCreateView.as_view(), name="site-create"),
    path("sites/<int:site_id>", api.SiteDetailView.as_view(), name="site-detail"),
    path(
        "sites/<int:site_id>/discover-links",
        api.DiscoverLinksView.as_view(),
        name="site-discover-links",
    ),
    path("sites/<int:site_id>/links", api.SiteLinksView.as_view(), name="site-links"),
    # US4 — server-side headless capture (FR-016..FR-019)
    path(
        "links/<int:link_id>/captures",
        api.CaptureStartView.as_view(),
        name="capture-start",
    ),
    path(
        "links/<int:link_id>/captures/list",
        api.LinkCaptureListView.as_view(),
        name="capture-list",
    ),
    path(
        "captures/<int:capture_session_id>/fail",
        api.CaptureFailView.as_view(),
        name="capture-fail",
    ),
    # US5 — table extraction (FR-020..FR-022)
    path(
        "links/<int:link_id>/extractions",
        api.ExtractionView.as_view(),
        name="link-extractions",
    ),
    path(
        "links/<int:link_id>/tables", api.LinkTablesView.as_view(), name="link-tables"
    ),
    # US6 — table classification (FR-023..FR-025)
    path(
        "links/<int:link_id>/classifications",
        api.ClassificationView.as_view(),
        name="link-classifications",
    ),
    # US7 — plan schema extraction (FR-026..FR-031)
    path("plan-schema", api.PlanSchemaView.as_view(), name="plan-schema"),
    path("links/<int:link_id>/plans", api.PlansView.as_view(), name="link-plans"),
    path(
        "links/<int:link_id>/plans/<int:plan_id>/ignore",
        api.PlanIgnoreView.as_view(),
        name="link-plan-ignore",
    ),
    # US8 — optional labeling (FR-032..FR-035)
    path(
        "links/<int:link_id>/labeling", api.LabelingView.as_view(), name="link-labeling"
    ),
    # US9 — publishing (FR-036..FR-038)
    path("links/<int:link_id>/publish", api.PublishView.as_view(), name="link-publish"),
    # US10 — replay, failure, alerts, re-run (FR-039..FR-046)
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
    path("links/<int:link_id>/rerun", api.LinkRerunView.as_view(), name="link-rerun"),
    path("alerts", api.AlertListView.as_view(), name="alerts"),
    # Settings and observability (FR-047, FR-054..FR-057)
    path("settings", api.SettingsView.as_view(), name="settings"),
    path("llm-token-budget", api.TokenBudgetView.as_view(), name="llm-token-budget"),
    path("metrics", api.MetricsView.as_view(), name="metrics"),
]
