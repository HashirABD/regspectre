"""cocotb bus driver for the uart_ctrl RTL.

Drives the Bus_Interface (we, re, addr, wdata, rdata) one transaction at a
time. Each transaction commits on one rising clk edge, and we and re are
deasserted once the transaction has committed.

cycle is the number of rising clk edges seen since the last reset.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge

SET = "SET"
CLR = "CLR"

MASK32 = 0xFFFFFFFF


def _check32(value):
    if not 0 <= value <= MASK32:
        raise ValueError(f"value {value:#x} does not fit in 32 bits")
    return value


class BusDriver:
    """Wraps a cocotb DUT that exposes the uart_ctrl bus signals."""

    def __init__(self, dut):
        self.dut = dut
        self.cycle = 0

    async def start(self, period_ns=10):
        """Start the clock, then reset the DUT."""
        cocotb.start_soon(Clock(self.dut.clk, period_ns, unit="ns").start())
        await self.reset()

    async def reset(self, cycles=2):
        """Hold rst_n low for the given number of edges, then release it.

        Also drives every input to 0 so no X values reach the RTL.
        cycle is set to 0 when rst_n is released.
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

    async def _tick(self):
        """Wait for one rising edge and count it."""
        await RisingEdge(self.dut.clk)
        self.cycle += 1
        return self.cycle

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