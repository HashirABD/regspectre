"""Static checks of the Studio source under web/.

This module statically checks the Studio source under web/. It reads files only,
and imports nothing from the engine. It needs no simulator, no network, no Node
tooling, and no external process.

Checks: absolute http and https URLs in web/ source (only BACKEND_URL in
web/lib/config.ts and the two localhost origins are allowed), no eval, no
new Function, no dangerouslySetInnerHTML, and no LLM or AI SDK package in
web/package.json.
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"

SKIP_DIRS = {"node_modules", ".next", "__pycache__"}
SKIP_FILES = {"next-env.d.ts"}
SOURCE_SUFFIXES = {".ts", ".tsx", ".mjs", ".js"}

# (relative POSIX path or "*" for any file, exact URL text)
ALLOWED_URLS = {
    ("web/lib/config.ts", "http://127.0.0.1:8000"),
    ("*", "http://localhost:3000"),
    ("*", "http://127.0.0.1:3000"),
}

ABSOLUTE_URL = re.compile(r"https?://[^\s\"'`)<>]+")

FORBIDDEN_TEXT = (
    re.compile(r"\beval\s*\("),
    re.compile(r"\bnew\s+Function\b"),
    re.compile(r"dangerouslySetInnerHTML"),
)

LLM_SDK_PACKAGES = (
    "openai",
    "@anthropic-ai/sdk",
    "@google/generative-ai",
    "cohere-ai",
    "langchain",
    "@langchain/core",
    "ollama",
    "@mistralai/mistralai",
)


def _relative(path):
    """Return the path relative to the repo root, with forward slashes."""
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def _walk(folder):
    """Yield every file under folder. Directories in SKIP_DIRS are not entered."""
    for entry in sorted(folder.iterdir()):
        if entry.is_dir():
            if entry.name not in SKIP_DIRS:
                yield from _walk(entry)
        elif entry.is_file():
            yield entry


def _source_files():
    """Return the Studio source files under web/, sorted. Empty if web/ does not exist."""
    if not WEB_DIR.is_dir():
        return []
    found = []
    for path in _walk(WEB_DIR):
        if path.name in SKIP_FILES or path.name.endswith(".tsbuildinfo"):
            continue
        if path.suffix in SOURCE_SUFFIXES:
            found.append(path)
    return sorted(found)


def _is_allowed(relative_path, url):
    """Return True when url is an allowed URL for the file at relative_path."""
    return any(
        url == allowed_url and allowed_path in ("*", relative_path)
        for allowed_path, allowed_url in ALLOWED_URLS
    )


def _disallowed_urls_in_text(relative_path, text):
    """Return (line number, URL text) for each absolute URL in text that is not allowed."""
    hits = []
    for line_number, line in enumerate(text.split("\n"), start=1):
        for match in ABSOLUTE_URL.finditer(line):
            if not _is_allowed(relative_path, match.group(0)):
                hits.append((line_number, match.group(0)))
    return hits


def _find_absolute_urls():
    """Return (relative path, line number, URL text) for each disallowed absolute URL under web/."""
    hits = []
    for path in _source_files():
        relative = _relative(path)
        text = path.read_text(encoding="utf-8")
        for line_number, url in _disallowed_urls_in_text(relative, text):
            hits.append((relative, line_number, url))
    return hits


def _forbidden_hits_in_text(text):
    """Return (line number, matched text) for each forbidden eval, new Function, or innerHTML use."""
    hits = []
    for line_number, line in enumerate(text.split("\n"), start=1):
        for pattern in FORBIDDEN_TEXT:
            for match in pattern.finditer(line):
                hits.append((line_number, match.group(0)))
    return hits


def test_web_source_folder_is_present_and_has_sources():
    assert WEB_DIR.is_dir(), f"web/ folder not found at {WEB_DIR}"
    relatives = [_relative(path) for path in _source_files()]
    assert relatives, "no Studio source files found under web/"
    assert "web/lib/config.ts" in relatives


def test_no_absolute_url_except_backend_and_localhost():
    hits = _find_absolute_urls()
    assert hits == [], f"disallowed absolute URLs as (path, line, URL): {hits}"


def test_backend_url_is_the_local_address():
    config = WEB_DIR / "lib" / "config.ts"
    assert config.is_file(), f"missing {config}"
    lines = config.read_text(encoding="utf-8").split("\n")
    assert 'export const BACKEND_URL = "http://127.0.0.1:8000";' in lines


def test_no_eval_new_function_or_inner_html():
    hits = []
    for path in _source_files():
        relative = _relative(path)
        text = path.read_text(encoding="utf-8")
        for line_number, matched in _forbidden_hits_in_text(text):
            hits.append((relative, line_number, matched))
    assert hits == [], f"forbidden eval, new Function, or dangerouslySetInnerHTML as (path, line, text): {hits}"


def test_no_llm_or_ai_sdk_in_package_json():
    package_json = WEB_DIR / "package.json"
    assert package_json.is_file(), f"missing {package_json}"
    data = json.loads(package_json.read_text(encoding="utf-8"))
    names = set(data.get("dependencies", {})) | set(data.get("devDependencies", {}))
    banned = sorted(names & set(LLM_SDK_PACKAGES))
    assert banned == [], f"LLM or AI SDK packages listed in web/package.json: {banned}"


def test_no_cloud_deployment_url_in_web_config():
    for name in ("next.config.mjs", "vitest.config.ts"):
        path = WEB_DIR / name
        assert path.is_file(), f"missing {path}"
        text = path.read_text(encoding="utf-8")
        assert ABSOLUTE_URL.search(text) is None, f"absolute URL found in web/{name}"


def test_scanner_finds_a_disallowed_url_and_a_forbidden_call():
    """Negative control: the scanner reports a non-allowed URL and a forbidden call, and allows localhost."""
    assert _disallowed_urls_in_text("web/lib/x.ts", 'const u = "https://example.com/a";') == [(1, "https://example.com/a")]
    assert _disallowed_urls_in_text("web/lib/x.ts", 'const o = "http://localhost:3000";') == []
    assert _forbidden_hits_in_text('const f = new Function("x");') == [(1, "new Function")]
