"""cocotb test for Property 8: a direct assignment never clears a neighbor W1C bit.

Requirement 9. The test issues UART_ISR = (1U << BIT) on the real uart_ctrl RTL under
random hw_set timing. It checks that no W1C bit other than BIT goes from set to cleared
across the write.

This is randomized testing, not proof of correctness. Hypothesis draws the hw_set
schedules, the write cycles and the target bits. A pass covers only the examples drawn
in that run. The test prints the number of examples that ran.

How Hypothesis and cocotb are combined. A cocotb coroutine cannot be awaited inside a
Hypothesis test, and Hypothesis rejects coroutine test functions. So the @given test
runs in a worker thread. For each drawn case, the worker puts the case on a queue and
waits for the answer. The cocotb side serves that queue. It runs each case on the RTL
and puts back "pass" or "fail". A failure is raised inside the @given function, so
Hypothesis shrinks it in the normal way. Only the cocotb side touches the DUT.

run_wipeout_check runs that pipeline for a write method that is passed in. The real test
passes direct_write. The test is listed in the uart_ctrl target of tests/Makefile.
"""

import queue
import threading

import cocotb
from cocotb.triggers import FallingEdge, Timer
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from engine.bus_driver import BusDriver
from engine.regmap import ISR_ADDR, bit_type

MAX_EXAMPLES = 100
REQUEST_POLL_NS = 10
RESULT_WAIT_S = 120.0

# W1C bits of UART_ISR, from regmap. A direct assignment targets one of these bits.
W1C_BITS = tuple(i for i in range(4) if bit_type("UART_ISR", i) == "W1C")

# hw_set bits used by the RTL. They are the W1C bits, because hwset_mask takes
# hw_set[0], hw_set[2] and hw_set[3]. hw_set bit 1 is not used, since the RTL drives
# bit 1 (RX_READY) from rx_valid.
HW_SET_MASK = sum(1 << i for i in W1C_BITS)
HW_SET_VALUES = tuple(v for v in range(16) if (v & ~HW_SET_MASK) == 0)


@st.composite
def timing_case(draw):
    """Draw one case: a per-cycle hw_set schedule, the write cycle, and the target BIT."""
    length = draw(st.integers(min_value=1, max_value=8))
    schedule = draw(st.lists(st.sampled_from(HW_SET_VALUES), min_size=length, max_size=length))
    write_at = draw(st.integers(min_value=0, max_value=length - 1))
    bit = draw(st.sampled_from(W1C_BITS))
    return tuple(schedule), write_at, bit


def _wiped_neighbours(pre, post, bit):
    """Return the W1C bits other than BIT that went from set to cleared."""
    return [i for i in W1C_BITS if i != bit and ((pre >> i) & 1) and not ((post >> i) & 1)]


async def direct_write(bus, bit):
    """Issue the direct assignment UART_ISR = (1U << bit). Returns the commit cycle."""
    return await bus.write(ISR_ADDR, 1 << bit)


async def _run_case(dut, bus, write_method, schedule, write_at, bit):
    """Run one case on the RTL. Returns ("pass", None) or ("fail", message).

    Each schedule entry is driven on the edge that follows the current point. The
    write commits on the edge that follows schedule[write_at]. The pre value is
    sampled at the falling edge just before that commit, and the post value is read
    right after the commit. write_method(bus, bit) issues the write and returns its
    commit cycle.
    """
    await bus.reset()
    pre = None
    post = None
    commit = None
    for k, hw in enumerate(schedule):
        dut.hw_set.value = hw
        if k == write_at:
            dut.addr.value = ISR_ADDR
            await FallingEdge(dut.clk)
            pre = int(dut.rdata.value)
            commit = await write_method(bus, bit)
            post, _ = await bus.read(ISR_ADDR)
        else:
            await bus.idle(1)

    wiped = _wiped_neighbours(pre, post, bit)
    if wiped:
        message = (
            f"neighbor wipeout: schedule={list(schedule)} BIT={bit} write_at={write_at} "
            f"commit_cycle={commit} pre={pre:#06b} post={post:#06b} cleared={wiped}"
        )
        return "fail", message
    return "pass", None


class _Bridge:
    """Queues shared by the Hypothesis worker thread and the cocotb side."""

    def __init__(self):
        self.requests = queue.Queue()
        self.results = queue.Queue()
        self.passed = 0
        self.sim_error = None
        self.hypothesis_error = None


def _hypothesis_worker(bridge):
    """Run the @given test. Each example is answered by the cocotb side."""

    @settings(
        max_examples=MAX_EXAMPLES,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(timing_case())
    def direct_write_keeps_neighbours(case):
        if bridge.sim_error is not None:
            raise RuntimeError("simulator stopped after an earlier error")
        bridge.requests.put(case)
        try:
            kind, value = bridge.results.get(timeout=RESULT_WAIT_S)
        except queue.Empty:
            raise RuntimeError("no answer from the simulator") from None
        if kind == "pass":
            bridge.passed += 1
        elif kind == "fail":
            raise AssertionError(value)
        else:
            raise RuntimeError("simulator error") from value

    try:
        direct_write_keeps_neighbours()
    except BaseException as exc:
        bridge.hypothesis_error = exc
    finally:
        bridge.requests.put(None)


async def _serve(dut, bus, bridge, write_method):
    """Answer each case from the worker thread until the worker sends None."""
    while True:
        try:
            case = bridge.requests.get_nowait()
        except queue.Empty:
            await Timer(REQUEST_POLL_NS, "ns")
            continue
        if case is None:
            return
        try:
            kind, value = await _run_case(dut, bus, write_method, *case)
        except Exception as exc:
            bridge.sim_error = exc
            bridge.results.put(("error", exc))
            return
        bridge.results.put((kind, value))


async def run_wipeout_check(dut, bus, write_method):
    """Run the Hypothesis pipeline and check every drawn case on the RTL.

    write_method(bus, bit) must issue the write on UART_ISR and return its commit cycle.
    Returns the number of examples that ran and passed. Raises AssertionError with the
    neighbor-wipeout message for a failing case, and re-raises any simulator or
    Hypothesis error.
    """
    bridge = _Bridge()
    worker = threading.Thread(target=_hypothesis_worker, args=(bridge,), daemon=True)
    worker.start()
    await _serve(dut, bus, bridge, write_method)
    worker.join(timeout=RESULT_WAIT_S)

    if worker.is_alive():
        raise AssertionError("Hypothesis worker did not finish")
    if bridge.sim_error is not None:
        raise bridge.sim_error
    if bridge.hypothesis_error is not None:
        raise bridge.hypothesis_error
    return bridge.passed


@cocotb.test()
async def test_pbt_hw_timing_direct_assignment_keeps_neighbours(dut):
    """Property 8 (Requirement 9): UART_ISR = (1U << BIT) clears no W1C bit other than BIT, under random hw_set timing.

    Randomized testing, not proof of correctness. The examples are drawn by Hypothesis,
    and only the examples drawn in this run are checked.
    """
    bus = BusDriver(dut)
    await bus.start()

    passed = await run_wipeout_check(dut, bus, direct_write)

    print(
        f"test_pbt_hw_timing: {passed} examples ran and passed "
        f"(max_examples={MAX_EXAMPLES}). Randomized testing, not proof of correctness."
    )
    assert passed >= MAX_EXAMPLES, f"only {passed} examples ran, need {MAX_EXAMPLES}"