"""Negative control for the Property 8 pipeline: it must fail for a bad RMW write.

tests/test_pbt_hw_timing.py runs its Property 8 check through run_wipeout_check. That
check must be able to fail. This file runs the same pipeline with a write that clears a
neighbor: the |= hero bug, UART_ISR |= (1U << BIT), done as one bus.rmw. The pipeline
must report a neighbor wipeout. If it does not, the pipeline cannot be trusted.

Timing of bus.rmw. The pipeline samples pre at the falling edge before the write call.
bus.rmw starts with a read, and that read waits for the next falling edge. So the rmw
write commits two rising edges after the pre sample, not one as direct_write does. The
rmw read samples the register one edge after pre. Any hw_set bit that arrives on that
edge is set in old but not in pre. That does not break the check. The RTL only sets W1C
bits from hw_set, and nothing clears them between pre and the commit, so pre is a subset
of old. A neighbor is still reported exactly when it was set in pre and hw_set does not
set it at the commit edge.

The pipeline is not changed. The import is the one function needed. The cocotb test of
that module is not imported, so cocotb does not collect it twice.

This is a directed control, not proof of correctness. The RTL is not modified.
"""

import cocotb

from engine.bus_driver import SET, BusDriver
from engine.regmap import ISR_ADDR
from test_pbt_hw_timing import run_wipeout_check


async def rmw_write(bus, bit):
    """Issue the |= hero bug UART_ISR |= (1U << bit) as one bus.rmw. Returns the commit cycle.

    bus.rmw returns (old, new, cycle). cycle is the commit cycle of its write, so it is
    returned here, as direct_write returns the commit cycle of its own write.
    """
    _, _, commit = await bus.rmw(ISR_ADDR, 1 << bit, SET)
    return commit


@cocotb.test()
async def test_pipeline_negative_control_rmw_hero_bug_fails_pipeline(dut):
    """The Property 8 pipeline must fail when the write is the |= hero bug done with bus.rmw.

    Pass: run_wipeout_check raises AssertionError whose text contains "neighbor wipeout".
    Fail: run_wipeout_check passes, or raises an AssertionError without that text.
    Any other exception is not caught, so it fails the test.
    """
    bus = BusDriver(dut)
    await bus.start()

    try:
        passed = await run_wipeout_check(dut, bus, rmw_write)
    except AssertionError as exc:
        text = str(exc)
        if "neighbor wipeout" not in text:
            raise AssertionError(
                f"pipeline negative control: AssertionError without 'neighbor wipeout': {text!r}"
            ) from exc
        print(text)
        print(
            "pipeline negative control: wipeout detected by the pipeline for the RMW hero bug "
            f"(exception type {type(exc).__name__})."
        )
        return

    raise AssertionError(
        "pipeline negative control: the pipeline did not detect the RMW hero bug, "
        f"it passed {passed} examples"
    )