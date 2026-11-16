"""End-to-end UART_ISR demo: C snippet to JSON violation reports on the real RTL.

run_c_source parses a C snippet, replays its operations on the uart_ctrl RTL
through a BusDriver, and returns the violation reports for each UART_ISR
operation. Part 8A: run_c_source replays UART_ISR operations only, and a UART_RDR
operation raises ValueError. Part 8B2: run_c_rdr_source replays UART_RDR read operations.
"""

from engine.bus_driver import BusDriver
from engine.c_parser import parse
from engine.detector import detect_rdr_double_reads, detect_violations
from engine.regmap import ISR_ADDR, RDR_ADDR
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

# Interrupt handler that reads UART_RDR twice. The second read sees the register that
# the first read cleared, so the received data is lost. This is the read-to-clear bug.
RDR_DOUBLE_READ_SNIPPET = """void uart_rdr_twice(void) {
    uint8_t first = UART_RDR;
    uint8_t second = UART_RDR;
}
"""

# Interrupt handler that reads UART_RDR once. This is the safe form.
RDR_SINGLE_READ_SNIPPET = """void uart_rdr_once(void) {
    uint8_t first = UART_RDR;
}
"""

# Data driven onto rx_data with rx_valid high for one edge before an RDR replay.
# 0xA5 is 1010_0101, so bits 0, 2, 5 and 7 are set. Every UART_RDR bit is read-to-clear.
RDR_RX_DATA = 0xA5


async def run_c_rdr_source(dut, source, seed=None, trace=None):
    """Replay a UART_RDR read snippet on the RTL and return (reports, json_text).

    The clock must already be running.

    seed: seeds the BusDriver hw_set noise, as in run_c_source. seed None is a quiet
    run. The noise reaches the RTL only through ISR bits, so it cannot change
    UART_RDR, which changes only on rx_valid and on an RDR read.

    Before the replay, RDR_RX_DATA is driven onto rx_data with rx_valid high for
    exactly one rising edge, and rx_valid is then lowered. BusDriver does not drive
    rx_valid or rx_data, so this is driven directly from dut. hw_set bit 1 is never
    driven here.

    Every READ operation is replayed with BusDriver.read, in program order. For each
    read:
    - value is the rdata returned at the falling edge before the read's commit edge.
      That is the value the register held before the read cleared it.
    - cycle is the commit rising edge of the read, where the read side effect lands.
    Each read gives one (op, value, cycle) tuple. detect_rdr_double_reads groups the
    tuples by op.handler and returns the reports. WRITE and RMW operations raise
    ValueError.

    Known gap: grouping is by handler name. Two separate invocations of the same
    handler name in one source are treated as one group, so a false report is possible.

    If trace is a dict, it is filled with:
    - "hw_log": the driver hw_log for this run, as (cycle, value) pairs.
    - "reads": one dict per READ with reg, handler, c_line, value and cycle.

    Returns (reports, json_text), where json_text is reports_to_json(reports).
    """
    bus = BusDriver(dut, seed=seed)
    await bus.reset()

    dut.rx_data.value = RDR_RX_DATA
    dut.rx_valid.value = 1
    await bus.idle(1)
    dut.rx_valid.value = 0

    reads = []
    reads_trace = []
    for op in parse(source):
        if op.kind != "READ":
            raise ValueError(f"RDR replay supports READ operations only, got {op.kind}")
        addr = RDR_ADDR if op.reg == "UART_RDR" else ISR_ADDR
        value, cycle = await bus.read(addr)
        reads.append((op, value, cycle))
        reads_trace.append(
            {
                "reg": op.reg,
                "handler": op.handler,
                "c_line": op.c_line,
                "value": value,
                "cycle": cycle,
            }
        )

    reports = detect_rdr_double_reads(reads)

    if trace is not None:
        trace["hw_log"] = list(bus.hw_log)
        trace["reads"] = reads_trace

    return reports, reports_to_json(reports)

USAGE = """usage: python3 -m engine.demo

The replays in this module drive the uart_ctrl RTL through cocotb, so they need the
RTL simulator (Icarus Verilog with cocotb 2.x). This entry point does not start the
simulator and does not print violation reports.

The runnable demo is tests/test_demo.py. Install the simulator, then run make in the
tests directory. The default target runs test_demo.py with the other uart_ctrl
modules. Those cocotb tests replay the ISR and RDR snippets on the RTL and check the
JSON reports.
"""


def format_report(json_text):
    """Return json_text unchanged, followed by one final newline."""
    if not isinstance(json_text, str):
        raise TypeError(f"json_text must be a str, got {type(json_text).__name__}")
    return json_text + "\n"


def main():
    print(USAGE, end="")


if __name__ == "__main__":
    main()