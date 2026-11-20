"""Pure request validation for POST /api/run.

This module is pure Python. It does no I/O, changes no globals, and imports no
web framework, so the rules run without a server.
"""

import json
from dataclasses import dataclass

from engine.c_parser import ParseError, parse_user_snippet
from engine.snippets import DEMO_SNIPPET_NAMES, DEMO_SOURCES

USER_SNIPPET = "USER_SNIPPET"
MAX_C_SOURCE_BYTES = 8192
MAX_C_SOURCE_LINES = 200

_DEMO_SOURCE_BY_NAME = dict(DEMO_SOURCES)
_NOT_PARSED = object()


def count_lines(text: str) -> int:
    """Count lines with the design 5.4 rule. The Studio's countLines matches it.

    The rule splits on "\\n" only, so U+2028 and other separators do not count.
    """
    if text == "":
        return 0
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.endswith("\n"):
        text = text[:-1]
    return len(text.split("\n"))


@dataclass(frozen=True)
class RunRequest:
    name: str
    source: str

    def as_run(self) -> list:
        """Return the one-element run list that run_replays takes."""
        return [{"name": self.name, "source": self.source}]


@dataclass(frozen=True)
class ErrorReply:
    status: int
    body: dict


def _invalid() -> ErrorReply:
    return ErrorReply(400, {"error": "invalid_request"})


def _decode_json(raw: bytes):
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return _NOT_PARSED


def validate_run_request(raw: bytes) -> RunRequest | ErrorReply:
    """Run Steps 1 to 3 of design 5.4 on a raw request body, in that order."""
    obj = _decode_json(raw)

    # Step 1, too_large.
    if isinstance(obj, dict) and isinstance(obj.get("c_source"), str):
        text = obj["c_source"]
        try:
            size = len(text.encode("utf-8"))
        except UnicodeEncodeError:
            return _invalid()
        if size > MAX_C_SOURCE_BYTES or count_lines(text) > MAX_C_SOURCE_LINES:
            return ErrorReply(400, {"error": "too_large"})

    # Step 2, invalid_request.
    if not isinstance(obj, dict):
        return _invalid()
    keys = set(obj)
    if keys == {"snippet"}:
        name = obj["snippet"]
        if not isinstance(name, str) or name not in DEMO_SNIPPET_NAMES:
            return _invalid()
        return RunRequest(name, _DEMO_SOURCE_BY_NAME[name])
    if keys == {"c_source"}:
        text = obj["c_source"]
        if not isinstance(text, str):
            return _invalid()

        # Step 3, parser_error.
        try:
            parse_user_snippet(text)
        except ParseError as exc:
            return ErrorReply(
                422, {"error": "parser_error", "line": exc.line, "message": exc.message}
            )
        return RunRequest(USER_SNIPPET, text)
    return _invalid()
