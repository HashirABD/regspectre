"""Real RTL tests for Replayed_State on rtl/uart_ctrl.sv.

Each test replays a C snippet through engine/demo.py on the RTL with quiet runs
(seed None) and checks the replayed_state that the replay fills in. The expected
values are derived from rtl/uart_ctrl.sv. They are not yet confirmed by a run, so
the first run must confirm them. If one differs, the test or the RTL is wrong, and
the cause must be found before the value is changed.

This module defines only cocotb test coroutines and helper functions. No helper
name starts with test_, so the module adds no other test collection (O5 guardrail).
"""

import cocotb

from engine.bus_driver import BusDriver
from engine.demo import run_c_rdr_source, run_c_source
from engine.snippets import (
    ISR_DIRECT_SNIPPET,
    ISR_RMW_SNIPPET,
    RDR_DOUBLE_READ_SNIPPET,
    RDR_SINGLE_READ_SNIPPET,
)

ISR_READ_ONLY_SOURCE = "void rd(void) {\n    uint32_t s = UART_ISR;\n}\n"
RDR_READ_SOURCE = "void rd(void) {\n    uint8_t d = UART_RDR;\n}\n"
RX_ON_READ = 0x3C


def assert_rdr_post(state, expected_post):
    """Raise AssertionError when the measured UART_RDR post value is not expected_post."""
    if state["post"] != expected_post:
        raise AssertionError(f"UART_RDR post is {state['post']}, expected {expected_post}")


async def assume_zero():
    """Broken post probe. It assumes the read cleared UART_RDR to 0."""
    return 0


def make_assume_pre(pre_value):
    """Return a broken post probe that assumes UART_RDR kept its first read value."""

    async def probe():
        return pre_value

    return probe


@cocotb.test()
async def test_isr_rmw_replayed_state(dut):
    """The |= snippet on pre 9 gives post 0. The write data is 9 | 1, and writing 1 clears bits 0 and 3."""
    bus = BusDriver(dut)
    await bus.start()

    trace = {}
    await run_c_source(dut, ISR_RMW_SNIPPET, seed=None, trace=trace)

    assert trace["replayed_state"] == {"register": "UART_ISR", "pre": 9, "post": 0}, (
        f"replayed_state: {trace['replayed_state']}"
    )


@cocotb.test()
async def test_isr_direct_replayed_state(dut):
    """The direct assignment on pre 9 gives post 8. Writing 1 clears bit 0 only, so bit 3 stays set."""
    bus = BusDriver(dut)
    await bus.start()

    trace = {}
    await run_c_source(dut, ISR_DIRECT_SNIPPET, seed=None, trace=trace)

    assert trace["replayed_state"] == {"register": "UART_ISR", "pre": 9, "post": 8}, (
        f"replayed_state: {trace['replayed_state']}"
    )


@cocotb.test()
async def test_isr_read_only_replayed_state_is_null(dut):
    """A snippet that only reads UART_ISR has no WRITE or RMW, so replayed_state is None and there is no report."""
    bus = BusDriver(dut)
    await bus.start()

    trace = {}
    reports, _ = await run_c_source(dut, ISR_READ_ONLY_SOURCE, seed=None, trace=trace)

    assert trace["replayed_state"] is None, f"replayed_state: {trace['replayed_state']}"
    assert reports == [], f"expected no report, got {reports}"


@cocotb.test()
async def test_rdr_double_read_replayed_state(dut):
    """The double read gives pre 165 and post 0. The first read returns 0xA5, and the second read clears UART_RDR."""
    bus = BusDriver(dut)
    await bus.start()

    trace = {}
    await run_c_rdr_source(dut, RDR_DOUBLE_READ_SNIPPET, seed=None, trace=trace)

    assert trace["replayed_state"] == {"register": "UART_RDR", "pre": 165, "post": 0}, (
        f"replayed_state: {trace['replayed_state']}"
    )


@cocotb.test()
async def test_rdr_single_read_replayed_state(dut):
    """The single read gives pre 165 and post 0. The read returns 0xA5 and clears UART_RDR on its commit edge."""
    bus = BusDriver(dut)
    await bus.start()

    trace = {}
    await run_c_rdr_source(dut, RDR_SINGLE_READ_SNIPPET, seed=None, trace=trace)

    assert trace["replayed_state"] == {"register": "UART_RDR", "pre": 165, "post": 0}, (
        f"replayed_state: {trace['replayed_state']}"
    )


@cocotb.test()
async def test_rdr_post_measured_after_rx_on_read(dut):
    """With rx_valid raised on the read's commit edge, post is 60 (0x3C). rx_valid wins over the read clear (rtl/uart_ctrl.sv line 47)."""
    bus = BusDriver(dut)
    await bus.start()

    trace = {}
    await run_c_rdr_source(dut, RDR_READ_SOURCE, seed=None, rx_on_read=RX_ON_READ, trace=trace)

    assert trace["replayed_state"] == {"register": "UART_RDR", "pre": 0, "post": 60}, (
        f"replayed_state: {trace['replayed_state']}"
    )


@cocotb.test()
async def test_rdr_post_negative_control(dut):
    """The post check passes with the real probe and fails with each broken probe.

    Scenario A: rx_on_read loads 0x3C on the commit edge, so the real post is 60.
    The broken probe assume_zero returns 0, and the check must raise.

    Scenario B: the double read leaves UART_RDR at 0. The broken probe returns the
    first read value 165, and the check must raise.
    """
    bus = BusDriver(dut)
    await bus.start()

    trace_a = {}
    await run_c_rdr_source(dut, RDR_READ_SOURCE, seed=None, rx_on_read=RX_ON_READ, trace=trace_a)
    assert_rdr_post(trace_a["replayed_state"], 60)

    trace_broken_a = {}
    await run_c_rdr_source(
        dut,
        RDR_READ_SOURCE,
        seed=None,
        rx_on_read=RX_ON_READ,
        post_probe=assume_zero,
        trace=trace_broken_a,
    )
    assume_zero_failed = False
    try:
        assert_rdr_post(trace_broken_a["replayed_state"], 60)
    except AssertionError:
        assume_zero_failed = True
    assert assume_zero_failed, "the assume_zero probe passed the post check, so the check cannot detect that bug"

    trace_b = {}
    await run_c_rdr_source(dut, RDR_DOUBLE_READ_SNIPPET, seed=None, trace=trace_b)
    assert_rdr_post(trace_b["replayed_state"], 0)

    pre = trace_b["replayed_state"]["pre"]
    trace_broken_b = {}
    await run_c_rdr_source(
        dut,
        RDR_DOUBLE_READ_SNIPPET,
        seed=None,
        post_probe=make_assume_pre(pre),
        trace=trace_broken_b,
    )
    assume_pre_failed = False
    try:
        assert_rdr_post(trace_broken_b["replayed_state"], 0)
    except AssertionError:
        assume_pre_failed = True
    assert assume_pre_failed, "the assume_pre probe passed the post check, so the check cannot detect that bug"
