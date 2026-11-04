"""Interface-boundary guard (Principle V, FR-034..FR-036)."""

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


@pytest.mark.parametrize("app", ["catalog", "notifications"])
def test_independent_modules_never_import_admin_console(app):
    root = _backend_root()
    for path in (root / app).rglob("*.py"):
        for name in _imports(path):
            assert not name.startswith("admin_console"), f"{path} imports {name}"


def test_admin_console_publishes_only_through_catalog_interface():
    root = _backend_root()
    for path in (root / "admin_console").rglob("*.py"):
        if path.name.startswith("test_"):
            continue
        for name in _imports(path):
            if name.startswith("catalog."):
                assert (
                    name == "catalog.interfaces"
                ), f"{path} imports {name}; publishing must go through CatalogInterface"
            assert (
                name != "catalog.models"
            ), f"{path} reaches into catalog.models directly"
