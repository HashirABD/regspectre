"""cocotb tests for engine/demo.py on the real uart_ctrl RTL.

Quiet runs (seed None) keep hw_set at 0 apart from the directed pulse. Their
pre state is exactly 0b1001, so their expected results are fixed.

Seeded runs add hw_set noise. Their expected reports are derived from the real
pre value and from the hw_set values logged in hw_log. The tests check the demo
against the RTL for these inputs. They do not prove the RTL correct.
"""

import json

import cocotb

from engine.bus_driver import BusDriver
from engine.demo import ISR_DIRECT_SNIPPET, ISR_RMW_SNIPPET, PRE_HW_SET, run_c_source

W1C_BITS = (0, 2, 3)
SEEDS = (7, 11, 13, 17, 19)


def _sampled_at(trace, cycle):
    """Return the hw_set value the RTL sampled at rising edge `cycle`.

    hw_log holds (cycle, value) for the value driven after that edge. The RTL
    samples that value at the next edge, so the value sampled at edge c is the
    value logged at c - 1.
    """
    return dict(trace["hw_log"])[cycle - 1]


def _check_isr_reports(reports, text, trace):
    """Check each report against the real pre value and the hw_set sampled at commit."""
    op = trace["ops"][0]
    pre = op["pre"]
    assert pre == PRE_HW_SET, f"first pre state should be {PRE_HW_SET:#06b}, got {pre:#06b}"
    sampled = _sampled_at(trace, op["cycle"])
    for report in reports:
        assert report.register == "UART_ISR", f"register: {report.register}"
        assert report.bit in W1C_BITS, f"bit {report.bit} is not a W1C bit"
        assert report.intended == 1, f"intended: {report.intended}"
        assert report.actual == 0, f"actual: {report.actual}"
        assert report.c_line == 2, f"c_line should be 2, got {report.c_line}"
        assert report.cycle == op["cycle"], f"cycle: {report.cycle} vs {op['cycle']}"
        assert ((pre >> report.bit) & 1) == 1, f"bit {report.bit} was not pending in the real pre value"
        assert ((sampled >> report.bit) & 1) == 0, f"hardware set bit {report.bit} on the commit edge"
    parsed = json.loads(text)
    assert [(r["register"], r["bit"]) for r in parsed] == [(r.register, r.bit) for r in reports]


def _expected_bit3_bits(trace):
    """Return the bits the |= snippet should report, given the logged hw_set.

    Bit 3 is pending in pre and is cleared by the write. A hardware set on the
    commit edge wins over that clear (Requirement 1.7). So the actual value of
    bit 3 equals the hw_set bit 3 sampled at commit. A report is expected exactly
    when that sampled bit is 0. Bit 0 is in the mask, so it is never reported.
    Bit 2 was not pending, so it is never reported.
    """
    sampled = _sampled_at(trace, trace["ops"][0]["cycle"])
    return [3] if ((sampled >> 3) & 1) == 0 else []


@cocotb.test()
async def test_demo_isr_rmw_snippet_reports_bit_3_once(dut):
    """Quiet run (seed None): the |= snippet on pre 0b1001 gives exactly one report for bit 3, at cycle 3 on line 2."""
    clock = BusDriver(dut)
    await clock.start()

    reports, text = await run_c_source(dut, ISR_RMW_SNIPPET, seed=None)

    assert len(reports) == 1, f"expected one violation, got {len(reports)}: {text}"
    report = reports[0]
    assert report.register == "UART_ISR", f"register: {report.register}"
    assert report.bit == 3, f"bit: {report.bit}"
    assert report.intended == 1, f"intended: {report.intended}"
    assert report.actual == 0, f"actual: {report.actual}"
    assert report.c_line == 2, f"c_line should be the |= statement on line 2, got {report.c_line}"
    assert report.cycle == 3, f"write should commit on cycle 3 after the pre state pulse, got {report.cycle}"
    assert json.loads(text) == [
        {"register": "UART_ISR", "bit": 3, "intended": 1, "actual": 0, "cycle": 3, "c_line": 2}
    ]


@cocotb.test()
async def test_demo_direct_assignment_snippet_gives_empty_report(dut):
    """Quiet run (seed None): the direct assignment clears only bit 0, so the report is empty."""
    clock = BusDriver(dut)
    await clock.start()

    reports, text = await run_c_source(dut, ISR_DIRECT_SNIPPET, seed=None)

    assert reports == [], f"expected no violations, got {reports}"
    assert text == "[]", f"expected empty JSON array, got {text}"


@cocotb.test()
async def test_demo_same_seed_gives_identical_json(dut):
    """Two |= runs with seed 7 give the same JSON string. Noise may mask bit 3, so the bit is not asserted here."""
    clock = BusDriver(dut)
    await clock.start()

    _, first = await run_c_source(dut, ISR_RMW_SNIPPET, seed=7)
    _, second = await run_c_source(dut, ISR_RMW_SNIPPET, seed=7)

    assert first == second, f"JSON differs between runs:\n{first}\n---\n{second}"


@cocotb.test()
async def test_demo_same_seed_gives_identical_json_and_hw_log(dut):
    """Two |= runs with seed 7 give the same JSON string and the same hw_log, and the noise is active."""
    clock = BusDriver(dut)
    await clock.start()

    first_trace = {}
    second_trace = {}
    _, first = await run_c_source(dut, ISR_RMW_SNIPPET, seed=7, trace=first_trace)
    _, second = await run_c_source(dut, ISR_RMW_SNIPPET, seed=7, trace=second_trace)

    assert first == second, f"JSON differs between runs:\n{first}\n---\n{second}"
    assert len(first_trace["hw_log"]) > 0, "seeded replay should log hw_set noise"
    assert first_trace["hw_log"] == second_trace["hw_log"], "hw_log differs between runs with the same seed"


@cocotb.test()
async def test_demo_isr_rmw_reports_follow_real_pre_and_hw_log_over_seeds(dut):
    """Over five seeds, the |= reports match the real pre value and the logged hw_set.

    Expected: bit 3 is reported exactly when the hw_set bit 3 sampled at the commit
    edge is 0, and no other bit is reported. Every reported bit is a W1C bit that
    was pending in the real pre value and was not set by hardware at commit.
    """
    clock = BusDriver(dut)
    await clock.start()

    for seed in SEEDS:
        trace = {}
        reports, text = await run_c_source(dut, ISR_RMW_SNIPPET, seed=seed, trace=trace)

        assert len(trace["ops"]) == 1, f"seed {seed}: expected one op, got {len(trace['ops'])}"
        _check_isr_reports(reports, text, trace)
        expected = _expected_bit3_bits(trace)
        got = [r.bit for r in reports]
        assert got == expected, f"seed {seed}: expected bits {expected}, got {got}"


@cocotb.test()
async def test_demo_direct_snippet_over_seeds_reports_nothing(dut):
    """Over five seeds, the direct assignment gives no report.

    Expected: an empty report for every seed. A direct write clears only its own bit,
    and detect_violations returns nothing for a WRITE. Any reported bit must also be
    pending in the real pre value.
    """
    clock = BusDriver(dut)
    await clock.start()

    for seed in SEEDS:
        trace = {}
        reports, text = await run_c_source(dut, ISR_DIRECT_SNIPPET, seed=seed, trace=trace)

        pre = trace["ops"][0]["pre"]
        assert pre == PRE_HW_SET, f"seed {seed}: first pre state should be {PRE_HW_SET:#06b}, got {pre:#06b}"
        for report in reports:
            assert ((pre >> report.bit) & 1) == 1, f"seed {seed}: bit {report.bit} was not pending in pre"
        assert reports == [], f"seed {seed}: expected no report, got {text}"
        assert text == "[]", f"seed {seed}: expected empty JSON array, got {text}"


@cocotb.test()
async def test_demo_two_seeds_complete_with_valid_reports(dut):
    """Two different seeds complete the replay, and their reports pass the same checks.

    The test does not assert that the two runs differ, because noise may or may not change the result.
    """
    clock = BusDriver(dut)
    await clock.start()

    for seed in (7, 8):
        trace = {}
        reports, text = await run_c_source(dut, ISR_RMW_SNIPPET, seed=seed, trace=trace)
        _check_isr_reports(reports, text, trace)