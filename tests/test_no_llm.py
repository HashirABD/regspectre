"""Static checks that engine/ makes no network or LLM calls.

These tests are pure Python. They parse each .py file under engine/ with ast and
never import the engine modules, so no simulator or cocotb is needed.

Limits: the scan finds import statements and direct calls to eval and exec. It
does not follow dynamic imports made with __import__ or importlib, and it does not
follow attribute calls such as builtins.eval. A clean scan shows that the source
has no forbidden import and no direct eval or exec call. It does not prove that
the code cannot reach the network at run time.
"""

import ast
from pathlib import Path

FORBIDDEN_MODULES = frozenset({
    "socket",
    "ssl",
    "http",
    "urllib",
    "requests",
    "httpx",
    "aiohttp",
    "websockets",
    "ftplib",
    "smtplib",
    "anthropic",
    "openai",
    "google",
    "cohere",
    "mistralai",
    "langchain",
    "litellm",
    "transformers",
})

FORBIDDEN_CALLS = frozenset({"eval", "exec"})

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"


def scan_source(source, filename="<string>"):
    """Return (kind, filename, line, name) for each forbidden import or call.

    kind is "import" or "call". name is the imported module or the called builtin.
    Results are sorted by line, so the output is deterministic.
    """
    tree = ast.parse(source, filename=filename)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_MODULES:
                    found.append(("import", filename, node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module and node.module.split(".")[0] in FORBIDDEN_MODULES:
                found.append(("import", filename, node.lineno, node.module))
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                found.append(("call", filename, node.lineno, node.func.id))
    return sorted(found, key=lambda item: (item[2], item[0], item[3]))


def engine_files():
    """Return every .py file under engine/, sorted by path."""
    return sorted(ENGINE_DIR.rglob("*.py"))


def scan_engine():
    """Scan every engine file and return all findings."""
    found = []
    for path in engine_files():
        found.extend(scan_source(path.read_text(encoding="utf-8"), str(path)))
    return found


def test_no_llm_engine_files_import_no_network_or_llm_modules():
    imports = [item for item in scan_engine() if item[0] == "import"]
    assert imports == [], f"forbidden imports in engine/: {imports}"


def test_no_llm_engine_files_do_not_call_eval_or_exec():
    calls = [item for item in scan_engine() if item[0] == "call"]
    assert calls == [], f"eval or exec calls in engine/: {calls}"


def test_no_llm_scan_covers_every_engine_file():
    names = {path.name for path in engine_files()}
    expected = {
        "__init__.py",
        "bus_driver.py",
        "c_parser.py",
        "demo.py",
        "detector.py",
        "intended_model.py",
        "regmap.py",
        "report.py",
    }
    assert expected <= names, f"engine files missing from the scan: {expected - names}"


def test_no_llm_scanner_detects_forbidden_import():
    """Negative test: the scanner flags a plain forbidden import, so a clean scan means something."""
    assert scan_source("import requests\n") == [("import", "<string>", 1, "requests")]


def test_no_llm_scanner_detects_forbidden_from_import_and_eval_exec():
    """Negative test: the scanner flags a forbidden from-import, an eval call and an exec call."""
    source = "from urllib.request import urlopen\nx = eval('1')\nexec('y = 2')\n"
    assert scan_source(source) == [
        ("import", "<string>", 1, "urllib.request"),
        ("call", "<string>", 2, "eval"),
        ("call", "<string>", 3, "exec"),
    ]


def test_no_llm_scanner_ignores_allowed_imports():
    """The scanner does not flag ordinary standard library imports or relative imports."""
    source = "import json\nfrom engine.regmap import REGISTERS\nfrom . import sibling\n"
    assert scan_source(source) == []