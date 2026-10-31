"""The single adapter module for the ``domtrack`` library (FR-000, SC-020).

Every ``import domtrack...`` in the backend lives here; ``test_domtrack_reuse.py``
walks the source tree and fails if it appears anywhere else.

:class:`DomtrackClient` wraps one domtrack capability per method and returns domtrack's
own result shape verbatim. Subclass it (or inject a fake) to test a stage without a
browser; the module-level functions delegate to :data:`default_client`.
"""

import json
import os


class DomtrackCaptureError(Exception):
    """domtrack was reachable but the headless recording itself failed (FR-018)."""


class DomtrackClient:
    """Server-side, headless domtrack adapter (FR-000c)."""

    # -- capture -----------------------------------------------------------

    def capture_headless(self, url, duration_ms, nav_timeout_ms=None):
        """Capture ``url`` headlessly and return the trace JSON bytes (FR-017).

        Navigates, waits for the page to settle, then records for the fixed
        ``duration_ms`` that headless capture requires. The page is **not** scrolled.
        """
        from playwright.sync_api import sync_playwright

        import domtrack

        timeout = int(nav_timeout_ms or 30000)
        config = domtrack.TracerConfig(
            url=url,
            headless=True,
            goto_timeout_ms=timeout,
            duration_ms=int(duration_ms),
            wait_until="domcontentloaded",
        )
        session = domtrack.CaptureSession(config)
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page(viewport=config.viewport)
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                    try:
                        page.wait_for_load_state("networkidle", timeout=3000)
                    except Exception:  # noqa: BLE001 - networkidle is best-effort
                        pass
                    session.install(page)
                    page.wait_for_timeout(int(duration_ms))
                    raw = session.collect(page)
                finally:
                    browser.close()
        except Exception as exc:  # noqa: BLE001 - surfaced as a capture failure
            raise DomtrackCaptureError(str(exc)) from exc
        return json.dumps(session.build_payload(raw)).encode("utf-8")

    # -- trace validity + loading -----------------------------------------

    def is_trace(self, raw):
        import domtrack

        return bool(domtrack.is_rrweb_trace(raw)) and bool((raw or {}).get("snapshot"))

    def load_trace(self, path):
        import domtrack

        raw = domtrack.load_raw(path)
        return raw, self.is_trace(raw)

    @staticmethod
    def read_trace_bytes(path):
        with open(path, "rb") as handle:
            return handle.read()

    @staticmethod
    def write_trace_bytes(data, path):
        if isinstance(data, (dict, list)):
            data = json.dumps(data).encode("utf-8")
        elif isinstance(data, str):
            data = data.encode("utf-8")
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    # -- tables ------------------------------------------------------------

    def extract_tables(self, path, min_rows=2, min_cols=2, dedupe=True):
        """Run ``domtrack tables extract``; return its result dict verbatim (FR-020)."""
        import domtrack
        from domtrack.tables.discovery import DiscoveryConfig, discover_tables

        raw = domtrack.load_raw(path)
        config = DiscoveryConfig(min_rows=min_rows, min_cols=min_cols, dedupe=dedupe)
        return discover_tables(raw, config)

    def label_tables(self, tables, label_config):
        """Run ``domtrack tables label``; return the labeled result (FR-033)."""
        from domtrack.tables.labeling import LabelConfig, label_tables as _label

        config = LabelConfig(
            provider=label_config.get("provider", "openai"),
            model=label_config.get("model") or None,
            base_url=label_config.get("base_url") or None,
            api_key=label_config.get("api_key") or os.environ.get("OPENAI_API_KEY"),
            lang=label_config.get("language", "fa"),
            batch_size=int(label_config.get("batch_size", 25)),
            dry_run=bool(label_config.get("dry_run", False)),
        )
        return _label({"tables": tables}, config)

    # -- replay / record / compare / diff ---------------------------------

    def compare_replay(self, before_path, replay_config=None, recording=None):
        """Run ``domtrack compare``: replay + record + diff in one call (FR-040)."""
        from domtrack.replay.compare import compare_replay as _compare
        from domtrack.replay.recording import RecordingConfig
        from domtrack.replay.replayer import ReplayConfig

        replay_config = replay_config or {}
        recording = recording or {}
        time_policy = replay_config.get("time_policy", "skip-aware")
        if time_policy not in ("faithful", "instant", "capped", "skip-aware"):
            time_policy = "skip-aware"
        rp = ReplayConfig(
            speed=float(replay_config.get("speed", 1.0)),
            mode=replay_config.get("mode", "all"),
            time_policy=time_policy,
            headless=True,
        )
        rec = RecordingConfig(
            enabled=True, output_dir=recording.get("output_dir", "traces")
        )
        return _compare(before_path, rp, rec)

    def diff_traces(self, before_path, after_path):
        """Run ``domtrack diff`` between two trace files (FR-040)."""
        import domtrack
        from domtrack.diff.core import diff_traces as _diff

        return _diff(domtrack.load_raw(before_path), domtrack.load_raw(after_path))

    def rebuild_dom(self, path, at_ms=None):
        """Run ``domtrack html`` to reconstruct a trace's DOM (operator diagnostics)."""
        import domtrack

        raw = domtrack.load_raw(path)
        state = domtrack.DomState.from_trace(raw)
        state.apply_up_to(raw.get("records") or [], at_ms)
        return state.to_html()


#: The default adapter instance the pipeline uses.
default_client = DomtrackClient()


def capture_headless(url, duration_ms, nav_timeout_ms=None):
    return default_client.capture_headless(url, duration_ms, nav_timeout_ms)


def is_trace(raw):
    return default_client.is_trace(raw)


def load_trace(path):
    return default_client.load_trace(path)


def extract_tables(path, min_rows=2, min_cols=2, dedupe=True):
    return default_client.extract_tables(path, min_rows, min_cols, dedupe)


def label_tables(tables, label_config):
    return default_client.label_tables(tables, label_config)


def compare_replay(before_path, replay_config=None, recording=None):
    return default_client.compare_replay(before_path, replay_config, recording)


def diff_traces(before_path, after_path):
    return default_client.diff_traces(before_path, after_path)


def rebuild_dom(path, at_ms=None):
    return default_client.rebuild_dom(path, at_ms)
