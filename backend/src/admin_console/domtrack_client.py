"""The single adapter module for the ``domtrack`` library (FR-000, SC-017).

Every ``import domtrack...`` in the backend lives here; ``test_domtrack_reuse.py`` walks
the source tree and fails if it appears anywhere else. Each function wraps one domtrack
capability and returns domtrack's own result shape verbatim — no stage re-derives what
domtrack already produced.
"""

import json
import os

import httpx
from django.conf import settings

from admin_console import constants


class DomtrackUnreachable(Exception):
    """The local domtrack REST API could not be reached (FR-017)."""


class DomtrackCaptureError(Exception):
    """domtrack was reachable but the recording itself failed (e.g. Chrome was closed)."""


# ---------------------------------------------------------------------------
# Local REST API (the operator's machine): capture + trace listing
# ---------------------------------------------------------------------------


def _local_base_url():
    return str(settings.DOMTRACK_LOCAL_API_URL).rstrip("/")


def local_health():
    """Probe the operator's ``domtrack serve`` without raising (used by the console)."""
    base = _local_base_url()
    try:
        response = httpx.get(
            f"{base}/health",
            timeout=min(5.0, float(settings.DOMTRACK_LOCAL_API_TIMEOUT_SECONDS)),
        )
    except httpx.HTTPError as exc:
        return {
            "reachable": False,
            "base_url": base,
            "error": str(exc)[:200],
        }
    if response.status_code >= 400:
        return {
            "reachable": False,
            "base_url": base,
            "status": response.status_code,
            "error": response.text[:200],
        }
    body = response.json()
    return {
        "reachable": True,
        "base_url": base,
        "name": body.get("name"),
        "version": body.get("version"),
        "trace_dir": body.get("trace_dir"),
    }


def start_local_capture(url, mode="interactive", duration_ms=None, selector=None):
    """Trigger ``domtrack capture`` through the local REST API (FR-012, FR-013).

    Returns domtrack's capture result; raises :class:`DomtrackUnreachable` when the
    operator's local service is down (mapped to ``502 domtrack_unreachable``).
    """
    if mode == "fixed_duration" and not duration_ms:
        duration_ms = constants.capture_fixed_duration_ms()
    interactive = mode != "fixed_duration" and not duration_ms
    payload = {
        "url": url,
        "selector": selector,
        "headless": not interactive,
    }
    if interactive:
        # Mirrors ``domtrack capture <url>`` without ``--duration``: the recorder calls
        # ``page.pause()`` and the operator presses Resume in the Playwright Inspector
        # when they are done, so there is no fixed recording window.
        payload["interactive"] = True
    else:
        payload["duration_s"] = max(1.0, float(duration_ms) / 1000.0)

    # An interactive recording waits for the operator, so it must not inherit the
    # fixed-duration read timeout. Keep the connect timeout short so a stopped
    # ``domtrack serve`` still fails fast.
    timeout = (
        httpx.Timeout(connect=5.0, read=None, write=30.0, pool=5.0)
        if interactive
        else float(settings.DOMTRACK_LOCAL_API_TIMEOUT_SECONDS)
    )
    try:
        response = httpx.post(
            f"{_local_base_url()}/capture",
            json=payload,
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        raise DomtrackUnreachable(str(exc)) from exc
    if interactive and response.status_code == 422 and "duration_s" in response.text:
        # Older domtrack servers reject the interactive flag; fall back to a bounded
        # recording window instead of failing the capture outright.
        payload.pop("interactive", None)
        payload["duration_s"] = max(
            1.0, constants.capture_interactive_duration_ms() / 1000.0
        )
        try:
            response = httpx.post(
                f"{_local_base_url()}/capture",
                json=payload,
                timeout=float(settings.DOMTRACK_LOCAL_API_TIMEOUT_SECONDS),
            )
        except httpx.HTTPError as exc:
            raise DomtrackUnreachable(str(exc)) from exc
    if response.status_code >= 400:
        raise DomtrackCaptureError(
            f"local domtrack returned {response.status_code}: {response.text[:200]}"
        )
    return response.json()


# ---------------------------------------------------------------------------
# Trace validity + loading (domtrack.trace)
# ---------------------------------------------------------------------------


def is_trace(raw):
    """Return whether ``raw`` is a domtrack (rrweb-style) trace."""
    import domtrack

    return bool(domtrack.is_rrweb_trace(raw)) and bool(
        (raw or {}).get("snapshot")
    )


def load_trace(path):
    """Load a trace file and return ``(raw, is_valid)``."""
    import domtrack

    raw = domtrack.load_raw(path)
    return raw, is_trace(raw)


def read_trace_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def write_trace_bytes(data, path):
    if isinstance(data, (dict, list)):
        data = json.dumps(data).encode("utf-8")
    elif isinstance(data, str):
        data = data.encode("utf-8")
    with open(path, "wb") as handle:
        handle.write(data)
    return path


# ---------------------------------------------------------------------------
# Table discovery + labeling (domtrack.tables)
# ---------------------------------------------------------------------------


def extract_tables(path, min_rows=2, min_cols=2, dedupe=True):
    """Run ``domtrack tables extract``; return domtrack's result dict verbatim (FR-018)."""
    import domtrack
    from domtrack.tables.discovery import DiscoveryConfig, discover_tables

    raw = domtrack.load_raw(path)
    config = DiscoveryConfig(min_rows=min_rows, min_cols=min_cols, dedupe=dedupe)
    return discover_tables(raw, config)


def label_tables(tables, label_config):
    """Run ``domtrack tables label``; return the labeled result (FR-021..FR-024).

    The API key is read from the environment only (Principle III).
    """
    from domtrack.tables.labeling import LabelConfig, label_tables as _label

    config = LabelConfig(
        provider=label_config.get("provider", "openai"),
        model=label_config.get("model") or None,
        base_url=label_config.get("base_url"),
        api_key=os.environ.get(
            "OPENAI_API_KEY"
            if label_config.get("provider", "openai") in ("openai", "compatible")
            else "ANTHROPIC_API_KEY"
        ),
        lang=label_config.get("language", "fa"),
        batch_size=int(label_config.get("batch_size", 25)),
        dry_run=bool(label_config.get("dry_run", False)),
    )
    return _label({"tables": tables}, config)


# ---------------------------------------------------------------------------
# Replay / record / compare / diff (domtrack.replay, domtrack.diff)
# ---------------------------------------------------------------------------


def compare_replay(before_path, replay_config, recording):
    """Run ``domtrack compare``: replay + record + diff (FR-038)."""
    from domtrack.replay.compare import compare_replay as _compare
    from domtrack.replay.recording import RecordingConfig
    from domtrack.replay.replayer import ReplayConfig

    rp = ReplayConfig(
        speed=float(replay_config.get("speed", 1.0)),
        mode=replay_config.get("mode", "clean"),
        time_policy=replay_config.get("time_policy", "skip-aware")
        if replay_config.get("time_policy")
        in ("faithful", "instant", "capped", "skip-aware")
        else "skip-aware",
        recording=RecordingConfig(
            enabled=True,
            output_dir=recording.get("output_dir", "traces"),
        ),
    )
    return _compare(before_path, rp)


def diff_traces(before_path, after_path):
    """Run ``domtrack diff`` between two trace files (FR-039)."""
    from domtrack.diff.core import diff_traces as _diff

    import domtrack

    return _diff(domtrack.load_raw(before_path), domtrack.load_raw(after_path))


def rebuild_dom(path, at_ms=None):
    """Run ``domtrack html`` to reconstruct a trace's DOM (diagnostics)."""
    import domtrack

    raw = domtrack.load_raw(path)
    state = domtrack.DomState.from_trace(raw)
    records = raw.get("records") or []
    state.apply_up_to(records, at_ms)
    return state.to_html()
