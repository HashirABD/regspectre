"""Tests for the count-line rule and the request size limits (design 5.4 and 7.1).

The count rule splits on LF only, after folding CRLF and CR into LF. It does not
treat VT, FF, NEL or U+2028 as line breaks. The U+2028 tests at the end pin down
that intended divergence between count_lines and the parser's line numbers.

Pure pytest. No simulator and no web framework.
"""

import json

import pytest

from backend.validation import (
    USER_SNIPPET,
    ErrorReply,
    RunRequest,
    count_lines,
    validate_run_request,
)
from engine.c_parser import KIND_WRITE, ParseError, parse_user_snippet

TOO_LARGE = {"error": "too_large"}
HEADER = "void h(void) {\n"
STATEMENT = " UART_ISR = (1U << TX_DONE);\n"
CLOSE = "}\n"
U2028 = "\u2028"


def _raw(text):
    return json.dumps({"c_source": text}).encode("utf-8")


def _is_too_large(result):
    return isinstance(result, ErrorReply) and result.body == TOO_LARGE


def _snippet_with_statements(count):
    return HEADER + STATEMENT * count + CLOSE


def _padded_snippet(total_bytes):
    """Return a snippet whose UTF-8 size is exactly total_bytes."""
    base_size = len((HEADER + CLOSE).encode("utf-8"))
    return HEADER + " " * (total_bytes - base_size) + CLOSE


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", 0),
        ("x", 1),
        ("x\n", 1),
        ("x\r\n", 1),
        ("x\r", 1),
        ("x\n\n", 2),
        ("a\u2028b", 1),
        ("a\x0bb", 1),
        ("a\x0cb", 1),
        ("a\x85b", 1),
    ],
)
def test_count_lines_rule(text, expected):
    assert count_lines(text) == expected


def test_200_line_snippet_is_accepted():
    text = _snippet_with_statements(198)
    assert count_lines(text) == 200
    result = validate_run_request(_raw(text))
    assert isinstance(result, RunRequest)
    assert result.name == USER_SNIPPET


def test_201_line_snippet_is_too_large():
    text = _snippet_with_statements(199)
    assert count_lines(text) == 201
    result = validate_run_request(_raw(text))
    assert isinstance(result, ErrorReply)
    assert result.status == 400
    assert result.body == TOO_LARGE


def test_8192_byte_snippet_is_not_too_large():
    text = _padded_snippet(8192)
    assert len(text.encode("utf-8")) == 8192
    result = validate_run_request(_raw(text))
    assert not _is_too_large(result)


def test_8193_byte_snippet_is_too_large():
    text = _padded_snippet(8193)
    assert len(text.encode("utf-8")) == 8193
    result = validate_run_request(_raw(text))
    assert isinstance(result, ErrorReply)
    assert result.body == TOO_LARGE


def test_4096_multibyte_chars_is_8192_bytes_not_too_large():
    text = "\u00e9" * 4096
    assert len(text.encode("utf-8")) == 8192
    result = validate_run_request(_raw(text))
    assert not _is_too_large(result)


def test_4097_multibyte_chars_is_8194_bytes_too_large():
    text = "\u00e9" * 4097
    assert len(text.encode("utf-8")) == 8194
    result = validate_run_request(_raw(text))
    assert isinstance(result, ErrorReply)
    assert result.body == TOO_LARGE


def test_u2028_snippet_counts_as_one_line_and_is_accepted():
    text = "void h(void) {" + U2028 + " UART_ISR = (1U << TX_DONE);" + U2028 + "}"
    assert count_lines(text) == 1
    result = validate_run_request(_raw(text))
    assert isinstance(result, RunRequest)


def test_u2028_snippet_write_is_on_c_line_2():
    text = "void h(void) {" + U2028 + " UART_ISR = (1U << TX_DONE);" + U2028 + "}"
    ops = parse_user_snippet(text)
    assert len(ops) == 1
    assert ops[0].kind == KIND_WRITE
    assert ops[0].c_line == 2


def test_u2028_loop_snippet_raises_parse_error_on_line_2():
    text = "void h(void) {" + U2028 + " for (;;) {}" + U2028 + "}"
    with pytest.raises(ParseError) as info:
        parse_user_snippet(text)
    assert info.value.line == 2


def test_u2028_loop_snippet_is_rejected_with_parser_error_on_line_2():
    text = "void h(void) {" + U2028 + " for (;;) {}" + U2028 + "}"
    result = validate_run_request(_raw(text))
    assert isinstance(result, ErrorReply)
    assert result.status == 422
    assert result.body["error"] == "parser_error"
    assert result.body["line"] == 2
