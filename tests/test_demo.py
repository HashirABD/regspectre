"""cocotb tests for engine/demo.py on the real uart_ctrl RTL.

These are directed tests. They check the UART_ISR demo against the RTL for one
pre state. Passing them is randomized-free evidence for this scenario only. It
does not prove the RTL correct.
"""

import json

import cocotb

from engine.bus_driver import BusDriver
from engine.demo import ISR_DIRECT_SNIPPET, ISR_RMW_SNIPPET, run_c_source


@cocotb.test()
async def test_demo_isr_rmw_snippet_reports_bit_3_once(dut):
    """The |= snippet clears pending bit 3, so exactly one report for bit 3 is produced."""
    clock = BusDriver(dut)
    await clock.start()

    reports, text = await run_c_source(dut, ISR_RMW_SNIPPET, seed=7)

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
    """The direct assignment clears only bit 0, so the report is empty."""
    clock = BusDriver(dut)
    await clock.start()

    reports, text = await run_c_source(dut, ISR_DIRECT_SNIPPET, seed=7)

    assert reports == [], f"expected no violations, got {reports}"
    assert text == "[]", f"expected empty JSON array, got {text}"


@cocotb.test()
async def test_demo_same_seed_gives_identical_json(dut):
    """Running the |= snippet twice with the same seed gives the same JSON string."""
    clock = BusDriver(dut)
    await clock.start()

    _, first = await run_c_source(dut, ISR_RMW_SNIPPET, seed=7)
    _, second = await run_c_source(dut, ISR_RMW_SNIPPET, seed=7)

    assert first == second, f"JSON differs between runs:\n{first}\n---\n{second}"
    assert json.loads(first)[0]["bit"] == 3