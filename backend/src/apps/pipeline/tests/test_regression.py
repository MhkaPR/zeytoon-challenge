"""Regression guards for the explicit design decisions in this feature.

Each test pins a behavior that was corrected during review so it cannot silently
regress: no page scroll during capture, the plan schema is a *list* of plans, the LLM
extracts data (never formulas/selectors), capture is server-side headless, there is no
sitemap step, and the external stages are small injectable classes.
"""

import pathlib

import pytest

from apps.pipeline import discovery, domtrack_client, llm, plan_schema
from apps.pipeline.services.v1 import pipeline as services

ROOT = pathlib.Path(__file__).resolve().parents[5]
ADMIN_CONSOLE = ROOT / "backend/src/apps/pipeline"


def test_capture_never_scrolls_the_page():
    source = (ADMIN_CONSOLE / "domtrack_client.py").read_text().lower()
    for scroll_api in (
        "mouse.wheel",
        "scroll_to",
        "scrollto",
        "window.scroll",
        "keyboard.press",
    ):
        assert scroll_api not in source
    assert "headless=true" in source.replace(" ", "")


def test_capture_session_uses_supported_domtrack_module():
    from domtrack.recorder import CaptureSession

    assert CaptureSession.__module__ == "domtrack.recorder"


def test_plan_schema_describes_a_list_of_plans():
    model = plan_schema.list_model("hosting")
    valid = {
        "plans": [
            {
                "plan_name": "A",
                "storage_amount": 1,
                "storage_unit": "GB",
                "ram_amount": 1,
                "cpu_cores": 1,
                "bandwidth_amount": 1,
                "price_amount": 1,
                "billing_period": "monthly",
            }
        ]
    }
    model.model_validate(valid)
    with pytest.raises(Exception):
        model.model_validate(valid["plans"][0])  # a bare plan item is not the unit


def test_no_formula_or_selector_module_exists():
    assert not (ADMIN_CONSOLE / "formulas.py").exists()
    assert not (ADMIN_CONSOLE / "cleaning.py").exists()


def test_feature_has_no_sitemap_step():
    # The pipeline modules that would host a sitemap step never mention one.
    for name in (
        "discovery.py",
        "services/v1/pipeline.py",
        "tasks.py",
        "constants.py",
    ):
        assert "sitemap" not in (ADMIN_CONSOLE / name).read_text().lower(), name
    from apps.pipeline.models import Site

    field_names = {field.name for field in Site._meta.get_fields()}
    assert not any("sitemap" in name for name in field_names)


def test_external_stages_are_subclassable_classes():
    assert isinstance(llm.default_client, llm.LlmClient)
    assert isinstance(llm.default_budget, llm.LlmBudget)
    assert isinstance(domtrack_client.default_client, domtrack_client.DomtrackClient)
    assert isinstance(discovery.default_discoverer, discovery.LinkDiscoverer)
    # Services call the adapters through these instances, so a subclass or fake can be
    # injected without touching the pipeline code.
    assert isinstance(
        services.domtrack_client.default_client, domtrack_client.DomtrackClient
    )
