"""Negative control for Property 8: the wipeout check must detect a real neighbor wipeout.

tests/test_pbt_hw_timing.py asserts that a direct assignment never clears a neighbor W1C
bit. A check that never fails shows nothing about its detection power. This file runs a
write that is known to clear a neighbor on the same real uart_ctrl RTL, and asserts that
the same wipeout condition reports it.

The write is the |= hero bug: a read-modify-write that writes back the read value with
BIT set. With pre 0b1001 and BIT 0, bit 3 is a pending neighbor, and the RMW clears it.

The directed case uses a quiet hw_set, so its result is fixed. The seeded cases run the
same RMW with seeded hw_set noise. For those cases the test checks the post value
against the hw_set values that the driver logged for the commit edge. Hardware set on
the commit edge wins over the write's clear (Requirement 1.7), so a post bit can be 1
when the write cleared it. That is expected and is not a failure.

The wipeout condition is _wiped_neighbours from tests/test_pbt_hw_timing.py, imported
by name, so this file and the real Property 8 test use the same function.

This is a directed control, not proof of correctness. The RTL is not modified.
"""

import cocotb

from engine.bus_driver import SET, BusDriver
from engine.regmap import ISR_ADDR
from test_pbt_hw_timing import _wiped_neighbours

# bit 0 (TX_DONE) and bit 3 (OVERRUN_ERR) are pending before the RMW. Bit 1 is not used,
# because the RTL drives bit 1 (RX_READY) from rx_valid.
PRE_HW_SET = 0b1001

# The bit the RMW names. Bit 3 is its pending neighbor.
TARGET_BIT = 0

SEEDS = (7, 11, 13, 17, 19)


def _hw_sampled_at(bus, cycle):
    """Return the hw_set value the RTL sampled at rising edge `cycle`.

    The driver logs (cycle, value) for the value driven after that edge, so the edge
    `cycle` samples the value logged at cycle - 1. A quiet run has no log and returns 0.
    """
    if not bus.hw_log:
        return 0
    return dict(bus.hw_log)[cycle - 1]


async def _run_hero_rmw(dut, bus, seed):
    """Pulse PRE_HW_SET, run |= (1U << TARGET_BIT) as an RMW, then read UART_ISR.

    Returns (pre, post, wiped, sampled). pre is the old value that BusDriver.rmw
    returns. sampled is the hw_set value the RTL sampled at the write's commit edge.
    """
    await bus.reset()
    dut.hw_set.value = PRE_HW_SET
    await bus.idle(1)
    if seed is None:
        # A seeded driver overwrites hw_set on each edge. A quiet run must clear it here.
        dut.hw_set.value = 0
    pre, _, commit = await bus.rmw(ISR_ADDR, 1 << TARGET_BIT, SET)
    post, _ = await bus.read(ISR_ADDR)
    sampled = _hw_sampled_at(bus, commit)
    return pre, post, _wiped_neighbours(pre, post, TARGET_BIT), sampled


@cocotb.test()
async def test_negative_control_rmw_hero_bug_is_detected(dut):
    """The wipeout check must detect the |= hero bug on the real RTL.

    Pass: the quiet directed case has pre 0b1001 and shows bit 3 wiped. Each seeded case
    has pre 0b1001, and its post bits match the hw_set values sampled at the commit edge.
    Fail: any of these checks does not hold.

    Not randomized testing and not Hypothesis. The seeded cases use the driver's seeded
    hw_set noise. They are counted and printed.
    """
    first = BusDriver(dut)
    await first.start()

    pre, post, wiped, _ = await _run_hero_rmw(dut, first, seed=None)
    print(f"negative control, quiet: pre={pre:#06b} post={post:#06b} wiped={wiped}")
    assert pre == PRE_HW_SET, f"quiet case: pre should be {PRE_HW_SET:#06b}, got {pre:#06b}"
    assert wiped == [3], (
        f"quiet case: expected neighbor wipeout of bit 3, got {wiped} "
        f"(pre={pre:#06b} post={post:#06b}). The wipeout check cannot be trusted."
    )

    detected = 1
    cases = 1
    for seed in SEEDS:
        bus = BusDriver(dut, seed=seed)
        seeded_pre, seeded_post, seeded_wiped, sampled = await _run_hero_rmw(dut, bus, seed=seed)
        print(
            f"negative control, seed {seed}: pre={seeded_pre:#06b} "
            f"post={seeded_post:#06b} wiped={seeded_wiped}"
        )

        assert seeded_pre == PRE_HW_SET, (
            f"seed {seed}: pre should be {PRE_HW_SET:#06b}, got {seeded_pre:#06b}"
        )
        assert ((seeded_post >> 1) & 1) == 0, (
            f"seed {seed}: bit 1 (RX_READY) should stay 0, post={seeded_post:#06b}"
        )
        # The write clears bit 0 and bit 3. Hardware set on the commit edge ORs back in.
        # So post bit 0 and post bit 3 equal the hw_set bits sampled at commit.
        assert ((seeded_post >> TARGET_BIT) & 1) == ((sampled >> TARGET_BIT) & 1), (
            f"seed {seed}: post bit {TARGET_BIT} should equal hw_set bit {TARGET_BIT} "
            f"sampled at commit ({sampled:#06b}), post={seeded_post:#06b}"
        )
        post_bit3 = (seeded_post >> 3) & 1
        assert post_bit3 == ((sampled >> 3) & 1), (
            f"seed {seed}: post bit 3 should equal hw_set bit 3 sampled at commit "
            f"({sampled:#06b}), post={seeded_post:#06b}"
        )

        # Expected, not a failure: when hardware sets bit 3 on the commit edge, post bit 3
        # is 1 and no wipeout is reported (hardware set wins, Requirement 1.7).
        if post_bit3 == 0:
            assert seeded_wiped == [3], (
                f"seed {seed}: post bit 3 is 0, so the wipeout of bit 3 should be reported, "
                f"got {seeded_wiped} (post={seeded_post:#06b})"
            )
        else:
            assert seeded_wiped == [], (
                f"seed {seed}: post bit 3 is 1, so no wipeout should be reported, "
                f"got {seeded_wiped} (post={seeded_post:#06b})"
            )

        cases += 1
        if seeded_wiped:
            detected += 1

    print(f"negative control: neighbor wipeout detected in {detected} of {cases} cases")