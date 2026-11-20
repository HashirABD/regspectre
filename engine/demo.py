"""End-to-end UART_ISR demo: C snippet to JSON violation reports on the real RTL.

run_c_source parses a C snippet, replays its operations on the uart_ctrl RTL
through a BusDriver, and returns the violation reports for each UART_ISR
operation. Part 8A: run_c_source replays UART_ISR operations only, and a UART_RDR
operation raises ValueError. Part 8B2: run_c_rdr_source replays UART_RDR read operations.
"""

import sys

from engine.bus_driver import BusDriver
from engine.c_parser import parse
from engine.detector import detect_rdr_double_reads, detect_violations
from engine.regmap import ISR_ADDR, RDR_ADDR
from engine.report import reports_to_json
from engine.replayed_state import isr_replayed_state, rdr_replayed_state
from engine.snippets import (
    DEMO_SNIPPET_NAMES, DEMO_SOURCES, ISR_RMW_SNIPPET, ISR_DIRECT_SNIPPET,
    RDR_DOUBLE_READ_SNIPPET, RDR_SINGLE_READ_SNIPPET,
)
from datetime import datetime, timezone
from engine.sim_runner import SimulationBusy, SimulationFailed, run_replays
from engine.snapshot import SNAPSHOT_PATH, build_snapshot, write_snapshot_atomic

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

    trace also receives "accesses" (every UART_ISR access in order) and
    "replayed_state" (isr_replayed_state of those accesses).

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
    accesses = []
    for op in parse(source):
        if op.reg != "UART_ISR":
            raise ValueError(f"part 8A replays UART_ISR only, got {op.reg}")
        if op.kind == "READ":
            value, _ = await bus.read(ISR_ADDR)
            accesses.append({"kind": "READ", "pre": value, "post": value})
            continue
        if op.kind == "WRITE":
            pre, _ = await bus.read(ISR_ADDR)
            cycle = await bus.write(ISR_ADDR, op.mask)
        elif op.kind == "RMW":
            pre, _, cycle = await bus.rmw(ISR_ADDR, op.mask, op.mode)
        else:
            raise ValueError(f"unknown operation kind {op.kind!r}")
        actual, _ = await bus.read(ISR_ADDR)
        accesses.append({"kind": op.kind, "pre": pre, "post": actual})
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
        trace["accesses"] = accesses
        trace["replayed_state"] = isr_replayed_state(accesses)

    return reports, reports_to_json(reports)

# Data driven onto rx_data with rx_valid high for one edge before an RDR replay.
# 0xA5 is 1010_0101, so bits 0, 2, 5 and 7 are set. Every UART_RDR bit is read-to-clear.
RDR_RX_DATA = 0xA5


async def run_c_rdr_source(dut, source, seed=None, trace=None, post_probe=None, rx_on_read=None):
    """Replay a UART_RDR read snippet on the RTL and return (reports, json_text).

    The clock must already be running.

    seed: seeds the BusDriver hw_set noise, as in run_c_source. seed None is a quiet
    run. The noise reaches the RTL only through ISR bits, so it cannot change
    UART_RDR, which changes only on rx_valid and on an RDR read.

    Before the replay, RDR_RX_DATA is driven onto rx_data with rx_valid high for
    exactly one rising edge, and rx_valid is then lowered. BusDriver does not drive
    rx_valid or rx_data, so this is driven directly from dut. hw_set bit 1 is never
    driven here.

    post_probe: an async callable that returns an int. None means the real probe,
    bus.peek(RDR_ADDR), sampled after the commit edge of the last read.

    rx_on_read: an int byte or None. When it is set, the standard RDR_RX_DATA pulse
    is skipped. rx_valid is raised with rx_data=rx_on_read for the commit edge of the
    last READ only, then lowered.

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
    - "replayed_state": rdr_replayed_state(pre, post), where pre is the first read's
      value and post is the value returned by the probe.

    Returns (reports, json_text), where json_text is reports_to_json(reports).
    """
    bus = BusDriver(dut, seed=seed)
    await bus.reset()

    ops = parse(source)
    last_read = max((i for i, op in enumerate(ops) if op.kind == "READ"), default=None)

    if rx_on_read is None:
        dut.rx_data.value = RDR_RX_DATA
        dut.rx_valid.value = 1
        await bus.idle(1)
        dut.rx_valid.value = 0

    reads = []
    reads_trace = []
    for i, op in enumerate(ops):
        if op.kind != "READ":
            raise ValueError(f"RDR replay supports READ operations only, got {op.kind}")
        addr = RDR_ADDR if op.reg == "UART_RDR" else ISR_ADDR
        is_last = rx_on_read is not None and i == last_read
        if is_last:
            dut.rx_data.value = rx_on_read
            dut.rx_valid.value = 1
        value, cycle = await bus.read(addr)
        if is_last:
            dut.rx_valid.value = 0
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

    if not reads:
        raise ValueError("RDR replay needs at least one READ operation")
    pre = reads[0][1]
    probe = post_probe if post_probe is not None else (lambda: bus.peek(RDR_ADDR))
    post = await probe()
    replayed_state = rdr_replayed_state(pre, post)

    if trace is not None:
        trace["hw_log"] = list(bus.hw_log)
        trace["reads"] = reads_trace
        trace["replayed_state"] = replayed_state

    return reports, reports_to_json(reports)


USAGE = """usage: python3 -m engine.demo [run]

With no argument, this message is printed and the simulator is not started.

run: replays the four demo snippets on the uart_ctrl RTL through cocotb, then prints
each snippet's name, C source and JSON report. Run it from the repo root with the
venv active. It needs Icarus Verilog and cocotb 2.x. Any other argument prints this
message to stderr and exits with status 2.

The cocotb tests in tests/test_demo.py check the same replays. Run make in the
tests directory to run them.
"""


def format_report(json_text):
    """Return json_text unchanged, followed by one final newline."""
    if not isinstance(json_text, str):
        raise TypeError(f"json_text must be a str, got {type(json_text).__name__}")
    return json_text + "\n"


def _fail(message):
    print(f"demo run failed: {message}", file=sys.stderr)
    return 1


def run_demo():
    """Replay the four demo snippets through run_replays, validate them, write the Snapshot, and print each record.

    Returns 0 only when the replays, the Snapshot checks, and the Snapshot write all succeed.
    A busy lock or a failed replay prints a message and returns 1, and nothing is written.
    """
    runs = [{"name": name, "source": source} for name, source in DEMO_SOURCES]
    try:
        records = run_replays(runs, timeout_s=None)
    except SimulationBusy:
        print("another simulation is running", file=sys.stderr)
        return 1
    except SimulationFailed as exc:
        return _fail(exc.message)
    created_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        payload = build_snapshot(records, created_utc)
        write_snapshot_atomic(SNAPSHOT_PATH, payload)
    except (ValueError, OSError) as exc:
        return _fail(f"the snapshot could not be written: {exc}")
    for record in records:
        print(f"== {record['name']} ==")
        print("C source:")
        print(record["source"], end="")
        print("report:")
        print(format_report(record["report"]), end="")
        print()
    return 0


def main(argv=None):
    """Print usage with no argument, or run the demo with the run argument.

    Returns the exit status.
    """
    args = sys.argv[1:] if argv is None else list(argv)
    if not args:
        print(USAGE, end="")
        return 0
    if args == ["run"]:
        return run_demo()
    print(USAGE, end="", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
