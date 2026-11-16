"""Hypothesis property tests for the engine, design Properties 1 to 7.

These tests are randomized. Hypothesis draws inputs, and each test checks one design
property on the drawn inputs. A pass is evidence for the inputs that were drawn. It
is not a proof that the engine is correct. derandomize=True makes each run draw the
same examples, so a failure can be reproduced.

Property 8 needs the uart_ctrl RTL and cocotb. It lives in tests/test_pbt_hw_timing.py
and is not in this file. Nothing here uses cocotb, a simulator or the network.

Properties 3 and 4 need the register value after a write. This file uses a test-side
model of the uart_ctrl W1C write rule with hw_set idle: a write clears each W1C bit
whose written bit is 1. The model is not the RTL.
"""

import json

from hypothesis import given, settings
from hypothesis import strategies as st

from engine.c_parser import Operation, parse
from engine.detector import Violation_Report, detect_rdr_double_reads, detect_violations
from engine.intended_model import intended_state
from engine.regmap import REGISTERS, bit_type
from engine.report import report_to_dict, reports_to_json

ISR_BITS = tuple(range(4))
ISR_W1C_BITS = tuple(i for i in ISR_BITS if bit_type("UART_ISR", i) == "W1C")
ISR_W1C_MASK = sum(1 << i for i in ISR_W1C_BITS)
ISR_NAMES = {i: REGISTERS["UART_ISR"]["bits"][i][0] for i in ISR_BITS}
RDR_RTC_BITS = tuple(i for i in range(8) if bit_type("UART_RDR", i) == "RTC")

# form name -> (Operation kind, Operation mode)
_FORMS = {"WRITE": ("WRITE", ""), "SET": ("RMW", "SET"), "CLR": ("RMW", "CLR")}
# C assignment operator -> (Operation kind, Operation mode)
_OPS = {"=": ("WRITE", ""), "|=": ("RMW", "SET"), "&=": ("RMW", "CLR")}


def _written(kind, mode, mask, pre):
    """Return the value the firmware writes to UART_ISR for this operation."""
    if kind == "WRITE":
        return mask & 0xF
    if mode == "SET":
        return (pre | mask) & 0xF
    return (pre & ~mask) & 0xF


def _rtl_actual(kind, mode, mask, pre):
    """Return UART_ISR after the write, with hw_set idle.

    A write clears each W1C bit whose written bit is 1. Bit 1 (RX_READY) is not
    writable, so it is never cleared by a write.
    """
    written = _written(kind, mode, mask, pre)
    return pre & ~(written & ISR_W1C_MASK) & 0xF


def _key(op):
    return (op.kind, op.reg, op.mask, op.mode)


def serialize(op):
    """Write an Operation back to a canonical UART_ISR statement (test-side helper).

    The mask must be non-zero and within bits 0 to 3. The engine has no serializer,
    so the round trip is checked with this helper.
    """
    bits = [i for i in ISR_BITS if (op.mask >> i) & 1]
    body = " | ".join(f"(1U << {ISR_NAMES[i]})" for i in bits)
    if op.kind == "WRITE":
        return f"UART_ISR = {body};"
    if op.kind == "RMW" and op.mode == "SET":
        return f"UART_ISR |= {body};"
    if op.kind == "RMW" and op.mode == "CLR":
        return f"UART_ISR &= ~({body});"
    raise ValueError(f"cannot serialize {op}")


@st.composite
def isr_statement(draw):
    """Draw one UART_ISR statement in the supported subset.

    Returns (text, kind, mask, mode). The mask is non-zero and within bits 0 to 3.
    Each bit is written by name or by index, in a random order. A single hex
    constant form is also drawn.
    """
    mask = draw(st.integers(min_value=1, max_value=15))
    op_text = draw(st.sampled_from(["=", "|=", "&="]))
    use_hex = draw(st.booleans())
    if use_hex:
        body = f"0x{mask:X}"
    else:
        bits = [i for i in ISR_BITS if (mask >> i) & 1]
        terms = []
        for bit in draw(st.permutations(bits)):
            by_name = draw(st.booleans())
            ref = ISR_NAMES[bit] if by_name else str(bit)
            terms.append(f"(1U << {ref})")
        body = " | ".join(terms)
    if op_text == "&=":
        expr = f"~{body}" if use_hex else f"~({body})"
    else:
        expr = body
    kind, mode = _OPS[op_text]
    return f"UART_ISR {op_text} {expr};", kind, mask, mode


@settings(max_examples=100, deadline=None, derandomize=True)
@given(isr_statement())
def test_property_1_parser_round_trip(case):
    """Property 1: For any statement in the supported C subset, parsing it into an Operation and serializing that Operation back to C-subset source yields an equivalent statement (same register, mask, and mode).

    Randomized test. The generator's expected kind, mask and mode are the oracle for parse().
    The round trip is checked on (kind, reg, mask, mode). It is not a text comparison.
    """
    text, kind, mask, mode = case
    ops = parse(text)
    assert len(ops) == 1, f"one statement should give one Operation: {text!r}"
    op = ops[0]
    assert _key(op) == (kind, "UART_ISR", mask, mode), f"{text!r} parsed as {op}"

    rebuilt = serialize(op)
    reparsed = parse(rebuilt)
    assert len(reparsed) == 1, f"serialized form should be one statement: {rebuilt!r}"
    assert _key(reparsed[0]) == _key(op), f"{text!r} -> {rebuilt!r} -> {reparsed[0]}"


@settings(max_examples=100, deadline=None, derandomize=True)
@given(
    form=st.sampled_from(["WRITE", "SET", "CLR"]),
    mask=st.integers(min_value=0, max_value=15),
    pre=st.integers(min_value=0, max_value=15),
)
def test_property_2_intended_state_respects_named_mask(form, mask, pre):
    """Property 2: For any operation naming bit mask M and any pre-operation register state, Intended_State[i] == pre[i] for every bit i outside M; and for every bit i inside M, Intended_State[i] equals the W1C write effect of the written value (0 if written[i]==1, else pre[i]).

    Randomized test. The written value is computed here, separately from the engine.
    Bit 1 (RX_READY) is read only. For that bit this test expects pre, as Requirement
    1.8 and the intended model do, not the 0 that the design's literal formula gives.
    """
    kind, mode = _FORMS[form]
    op = Operation(kind=kind, reg="UART_ISR", mask=mask, mode=mode, c_line=1)
    got = intended_state(op, pre)
    assert 0 <= got <= 0xF, f"intended state out of range: {got:#x}"

    written = _written(kind, mode, mask, pre)
    for i in ISR_BITS:
        pre_bit = (pre >> i) & 1
        if not (mask >> i) & 1:
            expected = pre_bit
        elif bit_type("UART_ISR", i) == "W1C":
            expected = 0 if (written >> i) & 1 else pre_bit
        else:
            expected = pre_bit
        assert ((got >> i) & 1) == expected, (
            f"{form} mask={mask:#06b} pre={pre:#06b}: bit {i} expected {expected}, got {got:#06b}"
        )


@settings(max_examples=100, deadline=None, derandomize=True)
@given(
    form=st.sampled_from(["SET", "CLR"]),
    mask=st.integers(min_value=0, max_value=15),
    pre=st.integers(min_value=0, max_value=15),
)
def test_property_3_rmw_flags_exactly_the_lost_neighbor_bits(form, mask, pre):
    """Property 3: For any read-modify-write on UART_ISR with pre-state pre and mask M, the detector emits one Violation_Report per bit i where Intended_State[i]==1 and Actual_State[i]==0 (every pending W1C bit outside M that the RMW cleared), and emits no other reports.

    Randomized test. The oracle is the set of pending W1C bits outside M. The actual
    value comes from the test-side W1C write model, not from the RTL.
    """
    op = Operation(kind="RMW", reg="UART_ISR", mask=mask, mode=form, c_line=7)
    actual = _rtl_actual("RMW", form, mask, pre)
    reports = detect_violations(op, pre=pre, actual=actual, cycle=5)

    expected_bits = [i for i in ISR_W1C_BITS if ((pre >> i) & 1) and not ((mask >> i) & 1)]
    assert [r.bit for r in reports] == expected_bits, (
        f"{form} mask={mask:#06b} pre={pre:#06b} actual={actual:#06b}: "
        f"expected bits {expected_bits}, got {[r.bit for r in reports]}"
    )
    for report in reports:
        assert report.register == "UART_ISR"
        assert report.intended == 1
        assert report.actual == 0
        assert report.cycle == 5
        assert report.c_line == 7


@settings(max_examples=100, deadline=None, derandomize=True)
@given(
    bit=st.integers(min_value=0, max_value=3),
    pre=st.integers(min_value=0, max_value=15),
)
def test_property_4_direct_assignment_produces_no_violations(bit, pre):
    """Property 4: For any direct assignment UART_ISR = (1U << BIT) and any pre-state, the detector emits zero Violation_Reports, because Intended_State == Actual_State (only the target bit changes, as intended).

    Randomized test. The test also checks Intended_State == Actual_State directly,
    so the empty result is not the only thing it relies on.
    """
    mask = 1 << bit
    op = Operation(kind="WRITE", reg="UART_ISR", mask=mask, mode="", c_line=3)
    actual = _rtl_actual("WRITE", "", mask, pre)
    assert intended_state(op, pre) == actual, (
        f"bit {bit} pre={pre:#06b}: intended {intended_state(op, pre):#06b} != actual {actual:#06b}"
    )
    assert detect_violations(op, pre=pre, actual=actual, cycle=2) == []


@settings(max_examples=100, deadline=None, derandomize=True)
@given(
    bit=st.sampled_from(ISR_BITS),
    blank_lines=st.integers(min_value=0, max_value=3),
    from_snippet=st.booleans(),
)
def test_property_5_c_line_presence_matches_source(bit, blank_lines, from_snippet):
    """Property 5: For any emitted Violation_Report, the c_line field is present if and only if the originating operation came from a parsed C snippet; it is omitted if and only if the operation came from a raw transaction list.

    Randomized test. A snippet is parsed, with 0 to 3 blank lines before it, so the
    expected c_line is known. A raw operation is built with c_line None. The pre state
    0b1111 guarantees at least one report.
    """
    if from_snippet:
        text = "\n" * blank_lines + f"UART_ISR |= (1U << {ISR_NAMES[bit]});"
        (op,) = parse(text)
        expected_line = blank_lines + 1
    else:
        op = Operation(kind="RMW", reg="UART_ISR", mask=1 << bit, mode="SET", c_line=None)
        expected_line = None

    pre = 0b1111
    actual = _rtl_actual("RMW", "SET", 1 << bit, pre)
    reports = detect_violations(op, pre=pre, actual=actual, cycle=4)
    assert reports, "pre 0b1111 with a one-bit mask always leaves pending neighbour W1C bits"
    for report in reports:
        record = report_to_dict(report)
        if expected_line is None:
            assert "c_line" not in record, f"raw operation should omit c_line: {record}"
        else:
            assert record["c_line"] == expected_line, f"c_line {record.get('c_line')} != {expected_line}"
        assert report.c_line == op.c_line


@settings(max_examples=100, deadline=None, derandomize=True)
@given(
    first=st.integers(min_value=0, max_value=255),
    second=st.integers(min_value=0, max_value=255),
    handler=st.sampled_from(["uart_rx", "uart_err"]),
    line_a=st.integers(min_value=1, max_value=50),
    line_b=st.integers(min_value=1, max_value=50),
)
def test_property_6_read_to_clear_double_read_detection(first, second, handler, line_a, line_b):
    """Property 6: For any interrupt handler, if UART_RDR is read twice, the detector emits one Violation_Report per bit that was 1 in the first read and 0 in the second (register=UART_RDR, intended=1, actual=0); if UART_RDR is read once, the detector emits no double-read Violation_Report.

    Randomized test. The two read values are drawn freely, so no RTL model is used.
    The expected bits are the RTC bits that were 1 in the first value and 0 in the second.
    """
    first_op = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=line_a, handler=handler)
    second_op = Operation(kind="READ", reg="UART_RDR", mask=0, mode="", c_line=line_b, handler=handler)

    reports = detect_rdr_double_reads([(first_op, first, 10), (second_op, second, 11)])
    expected_bits = [b for b in RDR_RTC_BITS if ((first >> b) & 1) == 1 and ((second >> b) & 1) == 0]
    assert [r.bit for r in reports] == expected_bits, (
        f"first={first:#04x} second={second:#04x}: expected {expected_bits}, got {[r.bit for r in reports]}"
    )
    for report in reports:
        assert report.register == "UART_RDR"
        assert report.intended == 1
        assert report.actual == 0
        assert report.cycle == 11
        assert report.c_line == line_b

    assert detect_rdr_double_reads([(first_op, first, 10)]) == []


@settings(max_examples=100, deadline=None, derandomize=True)
@given(
    register=st.sampled_from(["UART_ISR", "UART_RDR"]),
    bit=st.integers(min_value=0, max_value=7),
    intended=st.integers(min_value=0, max_value=1),
    actual=st.integers(min_value=0, max_value=1),
    cycle=st.integers(min_value=0, max_value=10**9),
    c_line=st.one_of(st.none(), st.integers(min_value=1, max_value=10**6)),
)
def test_property_7_report_json_validity_and_round_trip(register, bit, intended, actual, cycle, c_line):
    """Property 7: For any Violation_Report, serializing to JSON yields an object whose bit, intended, actual, and cycle fields have the required types (non-negative int; 0|1; 0|1; non-negative int), and parsing that JSON back yields an equivalent report.

    Randomized test. The types are checked on the parsed JSON, and then the report is
    rebuilt from the JSON and compared with the original.
    """
    report = Violation_Report(
        register=register, bit=bit, intended=intended, actual=actual, cycle=cycle, c_line=c_line
    )
    text = reports_to_json([report])
    records = json.loads(text)
    assert isinstance(records, list) and len(records) == 1, f"expected one record: {text}"
    record = records[0]

    assert type(record["bit"]) is int and record["bit"] >= 0
    assert type(record["cycle"]) is int and record["cycle"] >= 0
    assert type(record["intended"]) is int and record["intended"] in (0, 1)
    assert type(record["actual"]) is int and record["actual"] in (0, 1)
    if c_line is None:
        assert "c_line" not in record
    else:
        assert type(record["c_line"]) is int and record["c_line"] == c_line

    rebuilt = Violation_Report(
        register=record["register"],
        bit=record["bit"],
        intended=record["intended"],
        actual=record["actual"],
        cycle=record["cycle"],
        c_line=record.get("c_line"),
    )
    assert rebuilt == report, f"round trip changed the report: {report} -> {rebuilt}"