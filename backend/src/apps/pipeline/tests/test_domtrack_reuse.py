"""SC-020 — third-party captures stay behind their single adapter module."""

import ast
import pathlib

import pytest


def _backend_root():
    for candidate in (pathlib.Path("backend/src"), pathlib.Path("src")):
        if candidate.exists():
            return candidate
    pytest.skip("backend source root not found")


def _imports(path):
    tree = ast.parse(path.read_text())
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    return names


def _sources():
    for path in _backend_root().rglob("*.py"):
        if "test" in path.name or "migrations" in path.parts:
            continue
        yield path


def test_domtrack_is_imported_only_by_its_adapter():
    offenders = [
        path
        for path in _sources()
        if any(
            name == "domtrack" or name.startswith("domtrack.")
            for name in _imports(path)
        )
        and path.name != "domtrack_client.py"
    ]
    assert offenders == []


def test_crawl4ai_is_imported_only_by_discovery():
    offenders = [
        path
        for path in _sources()
        if any(
            name == "crawl4ai" or name.startswith("crawl4ai.")
            for name in _imports(path)
        )
        and path.name != "discovery.py"
    ]
    assert offenders == []


def test_no_module_shells_out_to_a_local_domtrack_server():
    offenders = [
        path for path in _sources() if "DOMTRACK_LOCAL_API_URL" in path.read_text()
    ]
    assert offenders == []
