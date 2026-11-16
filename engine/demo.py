"""End-to-end UART_ISR demo: C snippet to JSON violation reports on the real RTL.

run_c_source parses a C snippet, replays its operations on the uart_ctrl RTL
through a BusDriver, and returns the violation reports for each UART_ISR
operation. Part 8A replays UART_ISR operations only. A UART_RDR operation raises
ValueError.
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


async def run_c_source(dut, source, seed, trace=None):
    """Replay a UART_ISR C snippet on the RTL and return (reports, json_text).

    The clock must already be running.

    seed: the BusDriver hw_set noise is seeded with it, and the noise stays active
    for the whole replay. seed None gives a quiet replay, where hw_set is 0 except
    for the PRE_HW_SET pulse. The pulse is sampled before any noise is drawn, so the
    first operation always sees the pre state 0b1001.

    Timing rule for each WRITE or RMW:
    - pre is the UART_ISR value sampled at the falling edge after the last rising
      edge before the operation. For a WRITE, pre is a read just before the write.
      For an RMW, pre is the old value returned by rmw.
    - The write commits on the rising edge given by cycle, which is the cycle reported.
    - actual is sampled at the falling edge after the commit edge. Noise drawn at the
      commit edge reaches the RTL only at the next rising edge, so actual is the
      value right after the commit.

    Noise that reaches the RTL between pre and the commit sets bits that are not in
    pre. The detector treats those bits as not intended, so they cannot cause a
    report. Noise never clears a bit, so a pending bit is cleared only by a write.

    If trace is a dict, it is filled with:
    - "hw_log": the driver hw_log for this run, as (cycle, value) pairs.
    - "ops": one dict per WRITE or RMW with kind, reg, mask, mode, c_line, pre,
      actual and cycle.

    Returns (reports, json_text), where json_text is reports_to_json(reports).
    """
    bus = BusDriver(dut, seed=seed)
    await bus.reset()
    dut.hw_set.value = PRE_HW_SET
    await bus.idle(1)
    if seed is None:
        # A seeded driver overwrites hw_set itself on each edge. A quiet run must
        # clear it here, or the pulse would stay on.
        dut.hw_set.value = 0

    reports = []
    ops_trace = []
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
        ops_trace.append(
            {
                "kind": op.kind,
                "reg": op.reg,
                "mask": op.mask,
                "mode": op.mode,
                "c_line": op.c_line,
                "pre": pre,
                "actual": actual,
                "cycle": cycle,
            }
        )

    if trace is not None:
        trace["hw_log"] = list(bus.hw_log)
        trace["ops"] = ops_trace

    return reports, reports_to_json(reports)