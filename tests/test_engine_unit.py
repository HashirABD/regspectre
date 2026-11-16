"""Unit tests for engine components."""

import pytest

from engine.regmap import (
    REGISTERS,
    ISR_ADDR,
    RDR_ADDR,
    addr_to_name,
    bit_name_to_index,
    bit_type,
)
from engine.c_parser import Operation, ParseError, SymbolError, parse


def test_regmap_isr_address():
    assert REGISTERS["UART_ISR"]["addr"] == ISR_ADDR == 0x40001004


def test_regmap_rdr_address():
    assert REGISTERS["UART_RDR"]["addr"] == RDR_ADDR == 0x40001008


def test_regmap_isr_width():
    assert REGISTERS["UART_ISR"]["width"] == 4


def test_regmap_rdr_width():
    assert REGISTERS["UART_RDR"]["width"] == 8


def test_regmap_isr_bit_definitions():
    bits = REGISTERS["UART_ISR"]["bits"]
    assert bits[0] == ("TX_DONE", "W1C")
    assert bits[1] == ("RX_READY", "RO")
    assert bits[2] == ("PARITY_ERR", "W1C")
    assert bits[3] == ("OVERRUN_ERR", "W1C")


def test_regmap_rdr_bit_definitions():
    bits = REGISTERS["UART_RDR"]["bits"]
    assert len(bits) == 8
    for i in range(8):
        assert bits[i] == (f"RDR[{i}]", "RTC")


def test_regmap_addr_to_name_known():
    assert addr_to_name(ISR_ADDR) == "UART_ISR"
    assert addr_to_name(RDR_ADDR) == "UART_RDR"


def test_regmap_addr_to_name_unknown():
    with pytest.raises(KeyError):
        addr_to_name(0x40001000)


def test_regmap_bit_name_to_index_isr():
    assert bit_name_to_index("UART_ISR", "TX_DONE") == 0
    assert bit_name_to_index("UART_ISR", "RX_READY") == 1
    assert bit_name_to_index("UART_ISR", "PARITY_ERR") == 2
    assert bit_name_to_index("UART_ISR", "OVERRUN_ERR") == 3


def test_regmap_bit_name_to_index_rdr():
    assert bit_name_to_index("UART_RDR", "RDR[0]") == 0
    assert bit_name_to_index("UART_RDR", "RDR[7]") == 7


def test_regmap_bit_name_to_index_unknown():
    with pytest.raises(KeyError):
        bit_name_to_index("UART_ISR", "NONEXISTENT")


def test_regmap_bit_type_isr():
    assert bit_type("UART_ISR", 0) == "W1C"
    assert bit_type("UART_ISR", 1) == "RO"
    assert bit_type("UART_ISR", 2) == "W1C"
    assert bit_type("UART_ISR", 3) == "W1C"


def test_regmap_bit_type_rdr():
    for i in range(8):
        assert bit_type("UART_RDR", i) == "RTC"


def _parse_error_line(snippet):
    with pytest.raises(ParseError) as info:
        parse(snippet)
    return info.value.line


def test_parser_direct_assignment_maps_to_write():
    ops = parse("UART_ISR = (1U << TX_DONE);")
    assert ops == [Operation(kind="WRITE", reg="UART_ISR", mask=0b0001, mode="", c_line=1, handler="")]


def test_parser_compound_or_maps_to_rmw_set():
    ops = parse("UART_ISR |= (1U << TX_DONE);")
    assert ops == [Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=1, handler="")]


def test_parser_compound_and_maps_to_rmw_clr_with_cleared_bit_mask():
    ops = parse("UART_ISR &= ~(1U << PARITY_ERR);")
    assert ops == [Operation(kind="RMW", reg="UART_ISR", mask=0b0100, mode="CLR", c_line=1, handler="")]


def test_parser_read_into_local_maps_to_read_isr():
    ops = parse("uint32_t s = UART_ISR;")
    assert ops == [Operation(kind="READ", reg="UART_ISR", mask=0, mode="", c_line=1, handler="")]


def test_parser_rdr_read_maps_to_read_rdr():
    ops = parse("uint8_t d = UART_RDR;")
    assert ops == [Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=1, handler="")]


def test_parser_handler_scope_sets_handler_name():
    snippet = "\n".join([
        "void handler(void) {",
        "    uint8_t d = UART_RDR;",
        "    UART_ISR |= (1U << TX_DONE);",
        "}",
        "uint8_t e = UART_RDR;",
    ])
    assert parse(snippet) == [
        Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=2, handler="handler"),
        Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=3, handler="handler"),
        Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=5, handler=""),
    ]


def test_parser_hex_constant_and_comments_keep_line_numbers():
    snippet = "// setup\nUART_ISR |= 0x8; /* clear */"
    assert parse(snippet) == [Operation(kind="RMW", reg="UART_ISR", mask=0x8, mode="SET", c_line=2, handler="")]


def test_parser_multiline_statement_reports_first_line():
    snippet = "UART_ISR |= (1U << TX_DONE)\n    | (1U << OVERRUN_ERR);"
    assert parse(snippet) == [Operation(kind="RMW", reg="UART_ISR", mask=0b1001, mode="SET", c_line=1, handler="")]


def test_parser_c_line_counts_blank_lines():
    snippet = "UART_ISR = 0;\n\nUART_ISR |= (1U << OVERRUN_ERR);"
    assert parse(snippet) == [
        Operation(kind="WRITE", reg="UART_ISR", mask=0, mode="", c_line=1, handler=""),
        Operation(kind="RMW", reg="UART_ISR", mask=0b1000, mode="SET", c_line=3, handler=""),
    ]


def test_parser_rejects_for_loop_on_its_line():
    snippet = "UART_ISR = 0;\nfor (int i = 0; i < 4; i++) {\n    UART_ISR |= (1U << TX_DONE);\n}"
    assert _parse_error_line(snippet) == 2


def test_parser_rejects_while_loop_on_its_line():
    assert _parse_error_line("UART_ISR = 0;\nwhile (1) {\n}") == 2


def test_parser_rejects_if_conditional_on_its_line():
    assert _parse_error_line("UART_ISR = 0;\nif (UART_ISR) {\n}") == 2


def test_parser_rejects_ternary_conditional_on_its_line():
    assert _parse_error_line("UART_ISR |= (1U << TX_DONE) ? 1 : 0;") == 1


def test_parser_rejects_function_call_statement_on_its_line():
    assert _parse_error_line("UART_ISR = 0;\nclear_flags();") == 2


def test_parser_rejects_function_call_in_expression_on_its_line():
    assert _parse_error_line("UART_ISR |= read_bits(1);") == 1


def test_parser_rejects_pointer_dereference_on_its_line():
    assert _parse_error_line("*(volatile uint32_t *)0x40001004 = 1;") == 1


def test_parser_rejects_pointer_declaration_on_its_line():
    assert _parse_error_line("uint32_t *p = UART_ISR;") == 1


def test_parser_rejects_arithmetic_operator_on_its_line():
    assert _parse_error_line("UART_ISR = 1 + 1;") == 1


def test_parser_rejects_write_to_uart_rdr_on_its_line():
    assert _parse_error_line("UART_RDR = 0;") == 1


def test_parser_rejects_local_from_expression_on_its_line():
    assert _parse_error_line("uint32_t s = UART_ISR & 1;") == 1


def test_parser_rejects_bare_bit_name_on_its_line():
    assert _parse_error_line("UART_ISR |= TX_DONE;") == 1


def test_parser_rejects_unclosed_handler_at_its_opening_line():
    assert _parse_error_line("void handler(void) {\nUART_ISR = 0;") == 1


def test_parser_unknown_register_raises_symbol_error():
    with pytest.raises(SymbolError) as info:
        parse("UART_FOO = 1;")
    assert info.value.line == 1


def test_parser_unknown_bit_name_raises_symbol_error():
    with pytest.raises(SymbolError) as info:
        parse("UART_ISR |= (1U << BOGUS);")
    assert info.value.line == 1