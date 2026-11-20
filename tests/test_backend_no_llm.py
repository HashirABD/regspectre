"""Static checks that backend/ makes no LLM or forbidden network calls.

This file checks backend/ with the same static rules as tests/test_no_llm.py, and it
reuses that scanner (FORBIDDEN_MODULES, FORBIDDEN_CALLS and scan_source). The checks
cover import statements and direct eval or exec calls. The cocotb check is a regular
expression that matches an import at the start of a line. This is a static check, not
a proof: it does not follow dynamic imports, and it does not show that the running
Backend cannot reach the network.
"""

import re
from pathlib import Path

from test_no_llm import FORBIDDEN_CALLS, FORBIDDEN_MODULES, scan_source

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"


def _backend_files():
    """Return every .py file under backend/, sorted, skipping __pycache__ folders."""
    return sorted(
        path
        for path in BACKEND_DIR.rglob("*.py")
        if "__pycache__" not in path.relative_to(BACKEND_DIR).parts
    )


def _scan_backend(kind):
    """Scan every backend file and return the findings of one kind."""
    found = []
    for path in _backend_files():
        findings = scan_source(path.read_text(encoding="utf-8"), str(path))
        found.extend(item for item in findings if item[0] == kind)
    return found


def test_backend_folder_has_the_expected_files():
    assert BACKEND_DIR.is_dir(), f"backend/ folder not found at {BACKEND_DIR}"
    names = {path.name for path in _backend_files()}
    expected = {"__init__.py", "validation.py", "app.py"}
    assert expected <= names, f"backend files missing from the scan: {expected - names}"


def test_backend_imports_no_forbidden_module():
    imports = _scan_backend("import")
    assert imports == [], f"forbidden imports in backend/: {imports}"


def test_backend_makes_no_eval_or_exec_call():
    calls = _scan_backend("call")
    assert calls == [], f"eval or exec calls in backend/: {calls}"


def test_backend_does_not_import_cocotb():
    offenders = []
    for path in _backend_files():
        text = path.read_text(encoding="utf-8")
        if re.search(r"^\s*(import|from)\s+cocotb\b", text, re.M) is not None:
            offenders.append(str(path))
    assert offenders == [], f"cocotb imported in backend/: {offenders}"


def test_scanner_flags_a_forbidden_backend_import():
    """Negative test: the scanner flags a forbidden import and an eval call, so a clean scan means something."""
    assert "httpx" in FORBIDDEN_MODULES
    assert "eval" in FORBIDDEN_CALLS
    assert scan_source("import httpx\n") == [("import", "<string>", 1, "httpx")]
    assert scan_source("x = eval('1')\n") == [("call", "<string>", 1, "eval")]
