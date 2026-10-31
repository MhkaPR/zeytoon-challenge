"""T108 — the shared console API contract: auth, error shape, mounted prefix."""

import pytest

pytestmark = pytest.mark.django_db

GUEST_GET_ROUTES = [
    "/api/v1/ops/approvals",
    "/api/v1/ops/plan-schema",
    "/api/v1/ops/replay-runs",
    "/api/v1/ops/alerts",
    "/api/v1/ops/settings",
    "/api/v1/ops/llm-token-budget",
    "/api/v1/ops/metrics",
]


@pytest.mark.parametrize("route", GUEST_GET_ROUTES)
def test_guest_is_refused_on_every_console_route(api_client, route):
    response = api_client.get(route)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_error_body_shape_matches_the_contract(operator_client):
    response = operator_client.get("/api/v1/ops/links/999999/tables")

    assert response.status_code == 404
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "fields"}


def test_metrics_snapshot_exposes_pipeline_counters(operator_client):
    response = operator_client.get("/api/v1/ops/metrics")
    assert response.status_code == 200
    body = response.json()
    assert {
        "links_total",
        "links_published",
        "links_awaiting_budget",
        "links_dead_lettered",
        "open_alerts",
        "published_records",
        "llm_tokens_used",
    } <= set(body)


def test_settings_expose_runtime_tunables(operator_client):
    response = operator_client.get("/api/v1/ops/settings")
    assert response.status_code == 200
    values = response.json()["values"]
    assert "LINK_DENY_EXTENSIONS" in values
    assert "CAPTURE_FIXED_DURATION_MS" in values
    assert "REPLAY_PERIOD_HOURS" in values
