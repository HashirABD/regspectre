"""End-to-end UART_ISR demo: C snippet to JSON violation reports on the real RTL.

run_c_source parses a C snippet, replays its operations on the uart_ctrl RTL
through BusDriver, and returns the violation reports for each UART_ISR operation.
Part 8A replays UART_ISR operations only. A UART_RDR operation raises ValueError.
"""

from engine.bus_driver import BusDriver
from engine.c_parser import parse
from engine.detector import detect_violations
from engine.regmap import ISR_ADDR
from engine.report import reports_to_json

# Interrupt handler that sets TX_DONE with a read-modify-write. This is the bug.
ISR_RMW_SNIPPET = """void uart_isr(void) {
    UART_ISR |= (1U << TX_DONE);
}
"""

# The same handler written as a direct assignment. This form is safe.
ISR_DIRECT_SNIPPET = """void uart_isr(void) {
    UART_ISR = (1U << TX_DONE);
}
"""

# hw_set value applied for one edge before the snippet runs. It sets bit 0 (TX_DONE)
# and bit 3 (OVERRUN_ERR). Bit 1 is not used because the RTL drives it from rx_valid.
PRE_HW_SET = 0b1001

# Cycles of seeded background hw_set traffic run before the directed replay.
PREFIX_CYCLES = 16


async def run_c_source(dut, source, seed):
    """Replay a UART_ISR C snippet on the RTL and return (reports, json_text).

    The clock must already be running. The seed drives background hw_set traffic
    in an idle prefix. The DUT is then reset, so the prefix does not affect the
    replay. The replay itself keeps hw_set at 0 except for the PRE_HW_SET pulse,
    because the expected report depends on the exact pre state.

    For each WRITE, the pre value is read before the write. For each RMW, the pre
    value is the old value returned by rmw. The actual value is read after each
    operation. The cycle is the commit cycle of the write.
    """
    prefix = BusDriver(dut, seed=seed)
    await prefix.reset()
    await prefix.idle(PREFIX_CYCLES)

    bus = BusDriver(dut)
    await bus.reset()
    dut.hw_set.value = PRE_HW_SET
    await bus.idle(1)
    dut.hw_set.value = 0

    reports = []
    for op in parse(source):
        if op.reg != "UART_ISR":
            raise ValueError(f"part 8A replays UART_ISR only, got {op.reg}")
        if op.kind == "READ":
            await bus.read(ISR_ADDR)
            continue
        if op.kind == "WRITE":
            pre, _ = await bus.read(ISR_ADDR)
            cycle = await bus.write(ISR_ADDR, op.mask)
        elif op.kind == "RMW":
            pre, _, cycle = await bus.rmw(ISR_ADDR, op.mask, op.mode)
        else:
            raise ValueError(f"unknown operation kind {op.kind!r}")
        actual, _ = await bus.read(ISR_ADDR)
        reports.extend(detect_violations(op, pre=pre, actual=actual, cycle=cycle))

    return reports, reports_to_json(reports)