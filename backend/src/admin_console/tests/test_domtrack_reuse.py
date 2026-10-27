"""domtrack-reuse guard (FR-000, SC-017).

Every ``import domtrack`` / ``from domtrack ...`` in the backend must live in the single
adapter module; nothing else may reach into the library.
"""

import ast
import pathlib

import pytest

ADAPTER = pathlib.Path("backend/src/admin_console/domtrack_client.py")


def _backend_root():
    for candidate in (pathlib.Path("backend/src"), pathlib.Path("src")):
        if candidate.exists():
            return candidate
    pytest.skip("backend source root not found")


def test_domtrack_imports_only_in_the_adapter_module():
    root = _backend_root()
    offenders = []
    for path in root.rglob("*.py"):
        if path == ADAPTER:
            continue
        if path.name == "test_domtrack_reuse.py":
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            if any(m == "domtrack" or m.startswith("domtrack.") for m in modules):
                offenders.append(str(path))
    assert offenders == [], f"domtrack imported outside the adapter: {offenders}"
