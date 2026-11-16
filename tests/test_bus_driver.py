import cocotb
from cocotb.triggers import RisingEdge

from engine.bus_driver import CLR, BusDriver

ISR_ADDR = 0x40001004
RDR_ADDR = 0x40001008


@cocotb.test()
async def test_bus_read_and_w1c_write(dut):
    """Read an hw_set pulse through the bus driver, then clear one bit with a W1C write."""
    bus = BusDriver(dut)
    await bus.start()

    # hw_set bits 0 and 2 for exactly one rising edge, then back to 0
    dut.hw_set.value = 0b0101
    await RisingEdge(dut.clk)
    dut.hw_set.value = 0

    value, _ = await bus.read(ISR_ADDR)
    assert value == 0b0101, f"read after hw_set pulse: got {value:#06b}"

    await bus.write(ISR_ADDR, 0b0001)

    value, _ = await bus.read(ISR_ADDR)
    assert value == 0b0100, f"read after W1C write of bit 0: got {value:#06b}"


@cocotb.test()
async def test_bus_cycle_stamps(dut):
    """Cycle stamps: write takes 1 edge, read 1 edge, rmw 2 edges, idle(n) n edges."""
    bus = BusDriver(dut)
    await bus.start()
    assert bus.cycle == 0, f"cycle after start should be 0, got {bus.cycle}"

    n = await bus.write(ISR_ADDR, 0)
    assert n == 1, f"first write should commit on cycle 1, got {n}"
    assert bus.cycle == n, f"bus.cycle {bus.cycle} should equal write cycle {n}"

    _, r = await bus.read(ISR_ADDR)
    assert r == n + 1, f"read cycle should be {n + 1}, got {r}"

    _, _, m = await bus.rmw(ISR_ADDR, 0, CLR)
    assert m == r + 2, f"rmw cycle should be {r + 2}, got {m}"
    assert bus.cycle == m, f"bus.cycle {bus.cycle} should equal rmw cycle {m}"

    before = bus.cycle
    await bus.idle(3)
    assert bus.cycle == before + 3, f"idle(3) should advance cycle by 3, got {bus.cycle - before}"

    w2 = await bus.write(ISR_ADDR, 0)
    assert w2 == m + 4, f"write after idle(3) should be cycle {m + 4}, got {w2}"