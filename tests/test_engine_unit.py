"""Unit tests for engine components."""

import json

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
from engine.intended_model import intended_state
from engine.detector import Violation_Report, detect_rdr_double_reads, detect_violations
from engine.report import report_to_dict, reports_to_json


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


def test_intended_direct_assignment_clears_only_target_bit():
    op = Operation(kind="WRITE", reg="UART_ISR", mask=0b0001, mode="", c_line=1)
    assert intended_state(op, 0b1001) == 0b1000
    assert intended_state(op, 0b1111) == 0b1110


def test_intended_direct_assignment_on_zero_state_stays_zero():
    op = Operation(kind="WRITE", reg="UART_ISR", mask=0b0001, mode="", c_line=1)
    assert intended_state(op, 0b0000) == 0b0000


def test_intended_rmw_set_hero_bug_case_pre_1001_keeps_neighbor_bit_3():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=1)
    assert intended_state(op, 0b1001) == 0b1000


def test_intended_rmw_set_on_zero_state_stays_zero():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=1)
    assert intended_state(op, 0b0000) == 0b0000


def test_intended_rmw_set_on_all_pending_pre_1111_clears_only_bit_0():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=1)
    assert intended_state(op, 0b1111) == 0b1110


def test_intended_rmw_set_with_single_pending_neighbor_keeps_it():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=1)
    assert intended_state(op, 0b1000) == 0b1000


def test_intended_rmw_clr_pre_1111_keeps_named_bit_2_set():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0100, mode="CLR", c_line=1)
    assert intended_state(op, 0b1111) == 0b1111


def test_intended_rmw_clr_pre_0000_stays_zero():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0100, mode="CLR", c_line=1)
    assert intended_state(op, 0b0000) == 0b0000


def test_intended_rmw_clr_with_pending_neighbor_keeps_it():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0100, mode="CLR", c_line=1)
    assert intended_state(op, 0b1001) == 0b1001


def test_intended_read_of_isr_keeps_pre_value():
    op = Operation(kind="READ", reg="UART_ISR", mask=0, mode="", c_line=1)
    assert intended_state(op, 0b1011) == 0b1011


def test_intended_read_of_rdr_clears_read_to_clear_bits():
    op = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=1)
    assert intended_state(op, 0xA5) == 0x00
    assert intended_state(op, 0x00) == 0x00
    assert intended_state(op, 0xFF) == 0x00


def test_intended_ro_bit_written_keeps_pre_value():
    op = Operation(kind="WRITE", reg="UART_ISR", mask=0b0010, mode="", c_line=1)
    assert intended_state(op, 0b0010) == 0b0010


def test_intended_rejects_pre_wider_than_register():
    op = Operation(kind="WRITE", reg="UART_ISR", mask=0b0001, mode="", c_line=1)
    with pytest.raises(ValueError):
        intended_state(op, 0x10)


def test_detector_hero_bug_reports_exactly_bit_3():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=4)
    reports = detect_violations(op, pre=0b1001, actual=0b0000, cycle=7)
    assert reports == [Violation_Report(register="UART_ISR", bit=3, intended=1, actual=0, cycle=7, c_line=4)]


def test_detector_direct_assignment_keeping_neighbor_gives_no_report():
    op = Operation(kind="WRITE", reg="UART_ISR", mask=0b0001, mode="", c_line=2)
    assert detect_violations(op, pre=0b1001, actual=0b1000, cycle=5) == []


def test_detector_rmw_pre_1111_actual_0000_reports_bits_2_and_3_only():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=4)
    reports = detect_violations(op, pre=0b1111, actual=0b0000, cycle=9)
    assert [r.bit for r in reports] == [2, 3]
    assert all(r.intended == 1 and r.actual == 0 for r in reports)


def test_detector_rmw_pre_0000_gives_no_report():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=4)
    assert detect_violations(op, pre=0b0000, actual=0b0000, cycle=3) == []


def test_detector_single_pending_neighbor_cleared_is_reported():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=4)
    reports = detect_violations(op, pre=0b1000, actual=0b0000, cycle=8)
    assert reports == [Violation_Report(register="UART_ISR", bit=3, intended=1, actual=0, cycle=8, c_line=4)]


def test_detector_single_pending_neighbor_kept_gives_no_report():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=4)
    assert detect_violations(op, pre=0b1000, actual=0b1000, cycle=8) == []


def test_detector_rmw_clr_clearing_pending_neighbor_is_reported():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0100, mode="CLR", c_line=6)
    reports = detect_violations(op, pre=0b1100, actual=0b0100, cycle=6)
    assert [r.bit for r in reports] == [3]


def test_detector_report_cycle_and_c_line_come_from_arguments():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=12)
    reports = detect_violations(op, pre=0b1001, actual=0b0000, cycle=42)
    assert reports[0].cycle == 42
    assert reports[0].c_line == 12


def test_detector_raw_operation_report_has_no_c_line():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=None)
    reports = detect_violations(op, pre=0b1001, actual=0b0000, cycle=1)
    assert reports[0].c_line is None


def test_detector_plain_read_gives_no_report():
    op = Operation(kind="READ", reg="UART_ISR", mask=0, mode="", c_line=1)
    assert detect_violations(op, pre=0b1001, actual=0b0000, cycle=2) == []


def test_detector_rmw_pre_0010_actual_0000_gives_no_report():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=4)
    assert detect_violations(op, pre=0b0010, actual=0b0000, cycle=4) == []


def test_detector_rmw_pre_1011_actual_0010_reports_exactly_bit_3():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=4)
    reports = detect_violations(op, pre=0b1011, actual=0b0010, cycle=4)
    assert [r.bit for r in reports] == [3]


def test_detector_actual_wider_than_4_bits_raises_value_error():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=4)
    with pytest.raises(ValueError):
        detect_violations(op, pre=0b1001, actual=0b10000, cycle=4)


def test_detector_negative_cycle_raises_value_error():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=4)
    with pytest.raises(ValueError):
        detect_violations(op, pre=0b1001, actual=0b0000, cycle=-1)


def test_detector_rdr_single_read_gives_no_report():
    op = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=2, handler="handler")
    assert detect_rdr_double_reads([(op, 0xA5, 3)]) == []


def test_detector_rdr_two_reads_in_handler_report_each_bit_set_in_first():
    first = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=2, handler="handler")
    second = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=3, handler="handler")
    reports = detect_rdr_double_reads([(first, 0xA5, 4), (second, 0x00, 5)])
    assert [r.bit for r in reports] == [0, 2, 5, 7]
    assert all(r.register == "UART_RDR" and r.intended == 1 and r.actual == 0 for r in reports)


def test_detector_rdr_two_reads_with_zero_first_value_give_no_report():
    first = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=2, handler="handler")
    second = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=3, handler="handler")
    assert detect_rdr_double_reads([(first, 0x00, 4), (second, 0x00, 5)]) == []


def test_detector_rdr_isr_reads_around_rdr_reads_add_no_report():
    isr = Operation(kind="READ", reg="UART_ISR", mask=0, mode="", c_line=1, handler="handler")
    rdr1 = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=3, handler="handler")
    rdr2 = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=4, handler="handler")
    reads = [(isr, 0x0B, 1), (rdr1, 0x3C, 2), (isr, 0x0B, 3), (rdr2, 0x00, 4), (isr, 0x00, 5)]
    reports = detect_rdr_double_reads(reads)
    assert [r.bit for r in reports] == [2, 3, 4, 5]
    assert all(r.cycle == 4 and r.c_line == 4 for r in reports)


def test_detector_rdr_isr_reads_only_give_no_report():
    isr = Operation(kind="READ", reg="UART_ISR", mask=0, mode="", c_line=1, handler="handler")
    assert detect_rdr_double_reads([(isr, 0x0F, 1), (isr, 0x0F, 2)]) == []


def test_detector_rdr_third_read_in_handler_is_not_compared():
    rdr = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=2, handler="handler")
    reports = detect_rdr_double_reads([(rdr, 0xFF, 1), (rdr, 0x00, 2), (rdr, 0x00, 3)])
    assert len(reports) == 8
    assert all(r.cycle == 2 for r in reports)


def test_detector_rdr_reads_in_different_handlers_are_not_compared():
    in_a = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=2, handler="a")
    in_b = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=5, handler="b")
    assert detect_rdr_double_reads([(in_a, 0xFF, 1), (in_b, 0x00, 2)]) == []


def test_detector_rdr_reads_outside_any_handler_are_not_scoped():
    op = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=2, handler="")
    assert detect_rdr_double_reads([(op, 0xFF, 1), (op, 0x00, 2)]) == []


def test_detector_rdr_report_carries_second_read_cycle_and_c_line():
    first = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=2, handler="handler")
    second = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=7, handler="handler")
    reports = detect_rdr_double_reads([(first, 0x01, 10), (second, 0x00, 11)])
    assert reports == [Violation_Report(register="UART_RDR", bit=0, intended=1, actual=0, cycle=11, c_line=7)]


def test_detector_rdr_value_wider_than_8_bits_raises_value_error():
    op = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=2, handler="handler")
    with pytest.raises(ValueError):
        detect_rdr_double_reads([(op, 0x100, 1)])


def test_detector_rdr_negative_cycle_raises_value_error():
    op = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=2, handler="handler")
    with pytest.raises(ValueError):
        detect_rdr_double_reads([(op, 0x01, -1)])


def test_report_empty_violation_list_gives_valid_empty_array():
    text = reports_to_json([])
    assert text == "[]"
    assert json.loads(text) == []


def test_report_hero_bug_violation_has_expected_fields_in_fixed_order():
    report = Violation_Report(register="UART_ISR", bit=3, intended=1, actual=0, cycle=7, c_line=4)
    text = reports_to_json([report])
    parsed = json.loads(text)
    assert parsed == [{"register": "UART_ISR", "bit": 3, "intended": 1, "actual": 0, "cycle": 7, "c_line": 4}]
    assert list(parsed[0].keys()) == ["register", "bit", "intended", "actual", "cycle", "c_line"]


def test_report_rdr_violation_from_raw_list_omits_c_line():
    report = Violation_Report(register="UART_RDR", bit=5, intended=1, actual=0, cycle=88, c_line=None)
    parsed = json.loads(reports_to_json([report]))
    assert parsed == [{"register": "UART_RDR", "bit": 5, "intended": 1, "actual": 0, "cycle": 88}]
    assert "c_line" not in parsed[0]


def test_report_rdr_violation_from_snippet_keeps_c_line():
    report = Violation_Report(register="UART_RDR", bit=0, intended=1, actual=0, cycle=11, c_line=7)
    parsed = json.loads(reports_to_json([report]))
    assert parsed == [{"register": "UART_RDR", "bit": 0, "intended": 1, "actual": 0, "cycle": 11, "c_line": 7}]


def test_report_missing_c_line_is_omitted_not_written_as_null():
    report = Violation_Report(register="UART_ISR", bit=2, intended=1, actual=0, cycle=3, c_line=None)
    text = reports_to_json([report])
    assert "c_line" not in text
    assert "null" not in text


def test_report_several_violations_keep_input_order():
    reports = [
        Violation_Report(register="UART_ISR", bit=3, intended=1, actual=0, cycle=5, c_line=9),
        Violation_Report(register="UART_ISR", bit=0, intended=1, actual=0, cycle=5, c_line=9),
        Violation_Report(register="UART_ISR", bit=2, intended=1, actual=0, cycle=5, c_line=9),
    ]
    parsed = json.loads(reports_to_json(reports))
    assert [record["bit"] for record in parsed] == [3, 0, 2]


def test_report_same_input_called_twice_gives_identical_string():
    reports = [
        Violation_Report(register="UART_ISR", bit=3, intended=1, actual=0, cycle=7, c_line=4),
        Violation_Report(register="UART_RDR", bit=5, intended=1, actual=0, cycle=8, c_line=None),
    ]
    assert reports_to_json(reports) == reports_to_json(reports)


def test_report_output_from_detector_parses_back_to_expected_data():
    op = Operation(kind="RMW", reg="UART_ISR", mask=0b0001, mode="SET", c_line=4)
    reports = detect_violations(op, pre=0b1001, actual=0b0000, cycle=7)
    parsed = json.loads(reports_to_json(reports))
    assert parsed == [{"register": "UART_ISR", "bit": 3, "intended": 1, "actual": 0, "cycle": 7, "c_line": 4}]


def test_report_to_dict_rejects_object_that_is_not_a_violation_report():
    with pytest.raises(TypeError):
        report_to_dict({"register": "UART_ISR", "bit": 3, "intended": 1, "actual": 0, "cycle": 7})


def test_report_to_dict_rejects_intended_outside_0_or_1():
    report = Violation_Report(register="UART_ISR", bit=3, intended=2, actual=0, cycle=7, c_line=4)
    with pytest.raises(ValueError):
        report_to_dict(report)


def test_report_to_dict_rejects_bool_as_bit_index():
    report = Violation_Report(register="UART_ISR", bit=True, intended=1, actual=0, cycle=7, c_line=4)
    with pytest.raises(TypeError):
        report_to_dict(report)


def test_report_to_dict_rejects_negative_cycle():
    report = Violation_Report(register="UART_ISR", bit=3, intended=1, actual=0, cycle=-1, c_line=4)
    with pytest.raises(ValueError):
        report_to_dict(report)