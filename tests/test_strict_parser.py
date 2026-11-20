"""Strict parser tests for engine/c_parser.py.

These tests are pure Python. They need no simulator and do not import cocotb or engine.demo.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from engine.c_parser import (
    BLOCK_COMMENT,
    BOTH_REGISTERS,
    HEADER_FORM,
    NO_HANDLER,
    OUTSIDE,
    ParseError,
    _scan_lines,
    parse,
    parse_user_snippet,
)

# Byte-for-byte copies of the demo sources in engine/demo.py.
ISR_RMW_SNIPPET = """void uart_isr(void) {
    UART_ISR |= (1U << TX_DONE);
}
"""

ISR_DIRECT_SNIPPET = """void uart_isr(void) {
    UART_ISR = (1U << TX_DONE);
}
"""

RDR_DOUBLE_READ_SNIPPET = """void uart_rdr_twice(void) {
    uint8_t first = UART_RDR;
    uint8_t second = UART_RDR;
}
"""

RDR_SINGLE_READ_SNIPPET = """void uart_rdr_once(void) {
    uint8_t first = UART_RDR;
}
"""

DEMO_SOURCES = (
    ("ISR_RMW_SNIPPET", ISR_RMW_SNIPPET),
    ("ISR_DIRECT_SNIPPET", ISR_DIRECT_SNIPPET),
    ("RDR_DOUBLE_READ_SNIPPET", RDR_DOUBLE_READ_SNIPPET),
    ("RDR_SINGLE_READ_SNIPPET", RDR_SINGLE_READ_SNIPPET),
)

# Expected message texts. These copy the text that engine/c_parser.py builds.
RX_READY_MESSAGE = (
    "RX_READY is read-only and cannot be written; "
    "writable bits are TX_DONE, PARITY_ERR and OVERRUN_ERR"
)
RAW_WRITE_PREFIX = "UART_ISR write is not an accepted form"
UINT16_PREFIX = "a register read must be declared as uint8_t or uint32_t"

LINE_SEP = "\u2028"

OUTSIDE_SNIPPET = (
    "void h(void) {\n"
    " UART_ISR = (1U << TX_DONE);\n"
    "}\n"
    "UART_ISR = (1U << PARITY_ERR);"
)

BOTH_REGISTERS_SNIPPET = (
    "void h(void) {\n"
    " UART_ISR = (1U << TX_DONE);\n"
    " uint8_t d = UART_RDR;\n"
    "}"
)


def _wrap(body):
    """Put one body line inside void h(void) { ... } on lines 1 to 3."""
    return "void h(void) {\n" + body + "\n}"


def _raised(snippet):
    """Return the ParseError that parse_user_snippet raises for snippet."""
    with pytest.raises(ParseError) as info:
        parse_user_snippet(snippet)
    return info.value


def test_loop_body_is_rejected():
    err = _raised(_wrap(" for (;;) {}"))
    assert err.line == 2
    assert "loops are not supported" in err.message


def test_if_else_body_is_rejected_as_conditional():
    err = _raised(_wrap(" if (1) {}"))
    assert err.line == 2
    assert "conditionals are not supported" in err.message


def test_ternary_body_is_rejected_as_conditional():
    err = _raised(_wrap(" UART_ISR = (1U << TX_DONE) ? 1 : 0;"))
    assert err.line == 2
    assert err.message == "conditional expressions are not supported"


def test_call_body_is_rejected():
    err = _raised(_wrap(" UART_ISR = f();"))
    assert err.line == 2
    assert "function calls are not supported" in err.message


def test_pointer_body_is_rejected():
    err = _raised(_wrap(" *p = 1;"))
    assert err.line == 2
    assert "pointer arithmetic and dereference are not supported" in err.message


def test_uart_rdr_write_is_rejected_as_read_to_clear():
    err = _raised(_wrap(" UART_RDR = 0;"))
    assert err.line == 2
    assert "read-to-clear" in err.message


def test_unknown_register_is_rejected():
    err = _raised(_wrap(" UART_FOO = 1;"))
    assert err.line == 2
    assert "unknown name" in err.message


def test_unknown_bit_is_rejected():
    err = _raised(_wrap(" UART_ISR = (1U << FOO);"))
    assert err.line == 2
    assert "unknown bit" in err.message


def test_rx_ready_write_is_rejected_with_reject_message():
    err = _raised(_wrap(" UART_ISR |= (1U << RX_READY);"))
    assert err.line == 2
    assert err.message == RX_READY_MESSAGE


def test_raw_constant_write_is_rejected():
    err = _raised(_wrap(" UART_ISR = 5;"))
    assert err.line == 2
    assert err.message.startswith(RAW_WRITE_PREFIX)


def test_raw_index_write_is_rejected():
    err = _raised(_wrap(" UART_ISR = (1U << 2);"))
    assert err.line == 2
    assert err.message.startswith(RAW_WRITE_PREFIX)


def test_compound_expression_write_is_rejected():
    err = _raised(_wrap(" UART_ISR = (1U << TX_DONE) | (1U << PARITY_ERR);"))
    assert err.line == 2
    assert err.message.startswith(RAW_WRITE_PREFIX)


def test_uint16_read_declaration_is_rejected():
    err = _raised(_wrap(" uint16_t d = UART_ISR;"))
    assert err.line == 2
    assert err.message.startswith(UINT16_PREFIX)


def test_no_handler_for_bare_statement():
    err = _raised("UART_ISR = (1U << TX_DONE);")
    assert err.line == 1
    assert err.message == NO_HANDLER


def test_empty_text_has_no_handler():
    err = _raised("")
    assert err.line == 1
    assert err.message == NO_HANDLER


def test_statement_outside_handler_is_rejected():
    err = _raised(OUTSIDE_SNIPPET)
    assert err.line == 4
    assert err.message == OUTSIDE


def test_both_registers_in_one_snippet_are_rejected():
    err = _raised(BOTH_REGISTERS_SNIPPET)
    assert err.line == 3
    assert err.message == BOTH_REGISTERS


def test_block_comment_is_reported_by_line_scan():
    has_handler, errors = _scan_lines(["void h(void) {", " /* open", "}"])
    assert has_handler
    assert (2, BLOCK_COMMENT) in errors


def test_header_form_on_one_line_is_rejected():
    err = _raised("void h(void) { UART_ISR = (1U << TX_DONE); }")
    assert err.line == 1
    assert err.message == HEADER_FORM


def test_unclosed_handler_is_rejected():
    err = _raised("void h(void) {\n UART_ISR = (1U << TX_DONE);")
    assert err.line == 1
    assert "is not closed" in err.message


def test_precedence_01_empty_and_blank_text_have_no_handler():
    for snippet in ("", "   "):
        err = _raised(snippet)
        assert err.line == 1, snippet
        assert err.message == NO_HANDLER, snippet


def test_precedence_02_empty_handler_returns_empty_list():
    assert parse_user_snippet("void h(void) {}") == []


def test_precedence_03_statement_without_handler_gives_no_handler():
    err = _raised("UART_ISR = (1U << TX_DONE);")
    assert err.line == 1
    assert err.message == NO_HANDLER


def test_precedence_04_statement_after_handler_is_outside():
    err = _raised("void h(void) {\n UART_ISR = (1U << TX_DONE);\n}\nUART_ISR = (1U << PARITY_ERR);")
    assert err.line == 4
    assert err.message == OUTSIDE


def test_precedence_05_rx_ready_write_is_line_scan_error():
    err = _raised("void h(void) {\n UART_ISR |= (1U << RX_READY);\n}")
    assert err.line == 2
    assert err.message == RX_READY_MESSAGE


def test_precedence_06_raw_constant_write_is_line_scan_error():
    err = _raised("void h(void) {\n UART_ISR = 5;\n}")
    assert err.line == 2
    assert err.message.startswith(RAW_WRITE_PREFIX)


def test_precedence_07_second_register_is_reported_on_its_line():
    err = _raised("void h(void) {\n UART_ISR = (1U << TX_DONE);\n uint8_t d = UART_RDR;\n}")
    assert err.line == 3
    assert err.message == BOTH_REGISTERS


def test_precedence_08_second_register_wins_over_later_loop():
    snippet = "void h(void) {\n UART_ISR = (1U << TX_DONE);\n uint8_t d = UART_RDR;\n for (;;) {}\n}"
    err = _raised(snippet)
    assert err.line == 3
    assert err.message == BOTH_REGISTERS


def test_precedence_09_loop_inside_handler_is_parse_error():
    err = _raised("void h(void) {\n for (;;) {}\n}")
    assert err.line == 2
    assert "loops are not supported" in err.message


def test_precedence_10_loop_outside_handler_wins_over_no_handler():
    err = _raised("for (;;) {}")
    assert err.line == 1
    assert "loops are not supported" in err.message


def test_precedence_11_one_line_handler_with_statement_is_header_form():
    err = _raised("void h(void) { UART_ISR = (1U << TX_DONE); }")
    assert err.line == 1
    assert err.message == HEADER_FORM


def test_u2028_is_a_line_break_for_the_parser_but_not_for_line_count():
    snippet = "void h(void) {" + LINE_SEP + " UART_ISR = (1U << TX_DONE);" + LINE_SEP + "}"
    assert len(snippet.split("\n")) == 1
    ops = parse_user_snippet(snippet)
    assert len(ops) == 1
    assert ops[0].c_line == 2


def test_u2028_loop_statement_is_reported_on_line_two():
    snippet = "void h(void) {" + LINE_SEP + " for (;;) {}" + LINE_SEP + "}"
    err = _raised(snippet)
    assert err.line == 2
    assert "loops are not supported" in err.message


def test_accepted_snippet_equals_parse_output():
    snippet = "void h(void) {\n UART_ISR = (1U << TX_DONE);\n}"
    assert parse_user_snippet(snippet) == parse(snippet)


def test_demo_sources_are_accepted_and_match_parse_output():
    for name, source in DEMO_SOURCES:
        assert parse_user_snippet(source) == parse(source), name


def test_every_rejected_snippet_gives_int_line_and_str_message():
    bad_snippets = (
        "",
        "UART_ISR = (1U << TX_DONE);",
        "for (;;) {}",
        "void h(void) {\n for (;;) {}\n}",
        "void h(void) {\n UART_ISR = 5;\n}",
        OUTSIDE_SNIPPET,
        BOTH_REGISTERS_SNIPPET,
        "void h(void) { UART_ISR = (1U << TX_DONE); }",
        "void h(void) {\n UART_ISR = (1U << TX_DONE);",
        _wrap(" UART_RDR = 0;"),
        _wrap(" UART_ISR = (1U << FOO);"),
        _wrap(" uint16_t d = UART_ISR;"),
        _wrap(" *p = 1;"),
        "void h(void) {" + LINE_SEP + " for (;;) {}" + LINE_SEP + "}",
    )
    for snippet in bad_snippets:
        err = _raised(snippet)
        assert isinstance(err.line, int) and err.line >= 1, repr(snippet)
        assert isinstance(err.message, str), repr(snippet)


# Property tests (Hypothesis). Each test is randomized: Hypothesis draws inputs and
# the test checks one rule on them. A pass is evidence, not proof (design 7.7).

_TEXT_WITH_BREAKS = st.text(
    alphabet=st.one_of(
        st.characters(),
        st.sampled_from(["\n", "\r", "\x0b", "\x0c", "\x1c", "\x85", "\u2028", "\u2029"]),
    )
)

# Header and brace fragments, accepted statement fragments, and rejected statement
# fragments. Joining them with newlines reaches both the parse path and the scan path.
_FRAGMENTS = [
    "void h(void) {",
    "void handler_a(void) {",
    "void h2(void) {",
    "void h(void)",
    "{",
    "}",
    " UART_ISR = (1U << TX_DONE);",
    " UART_ISR |= (1U << PARITY_ERR);",
    " UART_ISR &= ~(1U << OVERRUN_ERR);",
    " uint32_t s = UART_ISR;",
    " uint8_t d = UART_RDR;",
    "UART_ISR = (1U << TX_DONE);",
    " for (;;) {}",
    " UART_RDR = 0;",
    " UART_ISR = 5;",
    " UART_ISR |= (1U << RX_READY);",
    " UART_FOO = 1;",
]

_ISR_BIT_NAMES = ["TX_DONE", "PARITY_ERR", "OVERRUN_ERR"]


def _isr_statement():
    """Strategy for one statement that names UART_ISR and uses an accepted form."""
    bit = st.sampled_from(_ISR_BIT_NAMES)
    return st.one_of(
        bit.map(lambda b: f"UART_ISR = (1U << {b});"),
        bit.map(lambda b: f"UART_ISR |= (1U << {b});"),
        bit.map(lambda b: f"UART_ISR &= ~(1U << {b});"),
        st.just("uint32_t s = UART_ISR;"),
    )


@st.composite
def _accepted_snippet(draw):
    """Draw a snippet that names one register and uses only accepted forms.

    The snippet has one or more handlers. Each handler has 0 to 3 statements, each on
    its own line with a leading space. Every handler header is "void NAME(void) {".
    """
    reg = draw(st.sampled_from(["isr", "rdr"]))
    if reg == "isr":
        statement = _isr_statement()
    else:
        statement = st.just("uint8_t d = UART_RDR;")
    names = draw(st.lists(st.sampled_from(["h", "handler_a", "h2"]), min_size=1, max_size=3))
    lines = []
    for name in names:
        lines.append(f"void {name}(void) {{")
        for stmt in draw(st.lists(statement, max_size=3)):
            lines.append(" " + stmt)
        lines.append("}")
    return "\n".join(lines)


def _assert_line_and_message(err):
    """Check the two fields that every ParseError must carry."""
    assert isinstance(err.line, int) and not isinstance(err.line, bool), repr(err.line)
    assert err.line >= 1, repr(err.line)
    assert isinstance(err.message, str), repr(err.message)


@settings(max_examples=100, deadline=None, derandomize=True)
@given(st.text())
def test_any_text_gives_parse_output_or_parse_error(text):
    """Design 7.6 P1, in the any-text form listed in design 7.1. Randomized test.

    For any text, parse_user_snippet either returns parse(text), or raises ParseError
    with an int line of at least 1 and a str message. Other exception types are not
    caught here, so they fail the test.
    """
    try:
        result = parse_user_snippet(text)
    except ParseError as e:
        _assert_line_and_message(e)
    else:
        assert result == parse(text)


@settings(max_examples=100, deadline=None, derandomize=True)
@given(_TEXT_WITH_BREAKS)
def test_property_2_parse_error_fields_on_arbitrary_text(text):
    """Design 7.6 P2, on arbitrary text that includes line breaks. Randomized test.

    Every ParseError from parse_user_snippet has an int line of at least 1 and a str
    message.
    """
    try:
        parse_user_snippet(text)
    except ParseError as e:
        _assert_line_and_message(e)


@settings(max_examples=100, deadline=None, derandomize=True)
@given(st.lists(st.sampled_from(_FRAGMENTS), max_size=8))
def test_property_2_parse_error_fields_on_fragment_snippets(fragments):
    """Design 7.6 P2, on snippets joined from fragments. Randomized test.

    The fragments are header, brace, accepted and rejected statements, joined with
    newlines. Every ParseError from parse_user_snippet has an int line of at least 1
    and a str message.
    """
    try:
        parse_user_snippet("\n".join(fragments))
    except ParseError as e:
        _assert_line_and_message(e)


@settings(max_examples=100, deadline=None, derandomize=True)
@given(_accepted_snippet())
def test_accepted_forms_equal_parse_and_never_raise(snippet):
    """Design 7.1 Hypothesis row 2, related to design 7.6 P1. Randomized test.

    A snippet built from the accepted forms, with one register and one or more
    handlers, returns parse(snippet) and does not raise.
    """
    assert parse_user_snippet(snippet) == parse(snippet)
