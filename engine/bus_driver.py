"""cocotb bus driver for the uart_ctrl RTL.

Drives the Bus_Interface (we, re, addr, wdata, rdata) one transaction at a
time. Each transaction commits on one rising clk edge, and we and re are
deasserted once the transaction has committed.

cycle is the number of rising clk edges seen since the last reset.

Seeded hw_set stimulus: when a seed is given, every counted rising edge draws
the hw_set value for the next cycle. Each of the HW_SET_WIDTH bits is set with
probability 1/8. Each draw is logged in hw_log as (cycle, value), where cycle
is the edge after which value was driven. Without a seed, hw_set stays 0.
reset() reseeds the generator, so every reset restarts the same hw_set
sequence and the same seed always gives the same hw_log.
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge

SET = "SET"
CLR = "CLR"

MASK32 = 0xFFFFFFFF

# Width of hw_set in rtl/uart_ctrl.sv: input wire [3:0] hw_set
HW_SET_WIDTH = 4


def _check32(value):
    if not 0 <= value <= MASK32:
        raise ValueError(f"value {value:#x} does not fit in 32 bits")
    return value


class BusDriver:
    """Wraps a cocotb DUT that exposes the uart_ctrl bus signals."""

    def __init__(self, dut, seed=None):
        if seed is not None and not isinstance(seed, int):
            raise TypeError(f"seed must be an int or None, got {type(seed).__name__}")
        self.dut = dut
        self.cycle = 0
        self.hw_log = []
        self._seed = seed
        self._rng = None if seed is None else random.Random(seed)

    async def start(self, period_ns=10):
        """Start the clock, then reset the DUT."""
        cocotb.start_soon(Clock(self.dut.clk, period_ns, unit="ns").start())
        await self.reset()

    async def reset(self, cycles=2):
        """Hold rst_n low for the given number of edges, then release it.

        Also drives every input to 0 so no X values reach the RTL, including
        hw_set. Clears hw_log. cycle is set to 0 when rst_n is released.
        When seeded, reset reseeds the generator, so every reset restarts the
        same hw_set sequence.
        """
        d = self.dut
        d.we.value = 0
        d.re.value = 0
        d.addr.value = 0
        d.wdata.value = 0
        d.hw_set.value = 0
        d.rx_valid.value = 0
        d.rx_data.value = 0
        d.rst_n.value = 0
        for _ in range(cycles):
            await RisingEdge(d.clk)
        d.rst_n.value = 1
        self.cycle = 0
        self.hw_log.clear()
        if self._seed is not None:
            self._rng = random.Random(self._seed)

    def _draw_hw_set(self):
        """Draw one hw_set value. Each bit is set with probability 1/8."""
        value = 0
        for bit in range(HW_SET_WIDTH):
            if self._rng.randrange(8) == 0:
                value |= 1 << bit
        return value

    async def _tick(self):
        """Wait for one rising edge and count it.

        When seeded, draw the hw_set value for the next cycle, drive it, and
        log it as (cycle, value). When unseeded, hw_set is not touched.
        """
        await RisingEdge(self.dut.clk)
        self.cycle += 1
        if self._rng is not None:
            value = self._draw_hw_set()
            self.dut.hw_set.value = value
            self.hw_log.append((self.cycle, value))
        return self.cycle

    async def idle(self, n=1):
        """Wait n rising edges with no bus activity.

        Each edge is counted in cycle, and hw_set keeps being driven.
        """
        if n < 0:
            raise ValueError(f"idle count must be >= 0, got {n}")
        d = self.dut
        d.we.value = 0
        d.re.value = 0
        for _ in range(n):
            await self._tick()

    async def write(self, addr, data):
        """Write data to addr. Returns the cycle of the commit edge."""
        _check32(data)
        d = self.dut
        d.we.value = 1
        d.re.value = 0
        d.addr.value = addr
        d.wdata.value = data
        cycle = await self._tick()
        d.we.value = 0
        return cycle

    async def read(self, addr):
        """Read addr. Returns (rdata, cycle).

        rdata is sampled at the falling edge, before the commit edge, so it
        is the value the register held before any read side effect. The
        read side effect lands on the commit edge (cycle).
        """
        d = self.dut
        d.we.value = 0
        d.re.value = 1
        d.addr.value = addr
        await FallingEdge(d.clk)
        value = int(d.rdata.value)
        cycle = await self._tick()
        d.re.value = 0
        return value, cycle

    async def peek(self, addr):
        """Return rdata without a read strobe, after the next falling edge."""
        self.dut.addr.value = addr
        self.dut.re.value = 0
        self.dut.we.value = 0
        await FallingEdge(self.dut.clk)
        return int(self.dut.rdata.value)

    async def rmw(self, addr, mask, mode):
        """Read-modify-write addr.

        SET writes old | mask (the |= case). CLR writes old & ~mask (the &= ~mask case).
        Returns (old, new, cycle), where cycle is the commit edge of the write.
        """
        _check32(mask)
        if mode not in (SET, CLR):
            raise ValueError(f"unknown rmw mode {mode!r}, expected SET or CLR")
        old, _ = await self.read(addr)
        if mode == SET:
            new = (old | mask) & MASK32
        else:
            new = (old & ~mask) & MASK32
        cycle = await self.write(addr, new)
        return old, new, cycle
