import cocotb
from cocotb.triggers import RisingEdge

from engine.bus_driver import CLR, SET, BusDriver

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


@cocotb.test()
async def test_rmw_set_wipes_neighbor(dut):
    """ISR |= bit 0 writes back the pending bit 3 as 1, which clears bit 3."""
    bus = BusDriver(dut)
    await bus.start()

    # hw_set bits 0 and 3 for exactly one rising edge, then back to 0
    dut.hw_set.value = 0b1001
    await RisingEdge(dut.clk)
    dut.hw_set.value = 0

    old, new, _ = await bus.rmw(ISR_ADDR, 0b0001, SET)
    assert old == 0b1001, f"rmw old value: got {old:#06b}"
    assert new == 0b1001, f"rmw new value: got {new:#06b}"

    value, _ = await bus.read(ISR_ADDR)
    assert value == 0b0000, f"bit 3 should be wiped by the RMW, ISR={value:#06b}"


@cocotb.test()
async def test_direct_write_keeps_neighbor(dut):
    """A direct write to bit 0 leaves the pending neighbor bit 3 set."""
    bus = BusDriver(dut)
    await bus.start()

    # hw_set bits 0 and 3 for exactly one rising edge, then back to 0
    dut.hw_set.value = 0b1001
    await RisingEdge(dut.clk)
    dut.hw_set.value = 0

    await bus.write(ISR_ADDR, 0b0001)

    value, _ = await bus.read(ISR_ADDR)
    assert value == 0b1000, f"bit 3 should survive a direct write to bit 0, ISR={value:#06b}"


@cocotb.test()
async def test_rdr_read_to_clear_via_driver(dut):
    """rx_valid loads UART_RDR and sets RX_READY. The first RDR read clears both."""
    bus = BusDriver(dut)
    await bus.start()

    # Drive rx_valid high for exactly one rising edge with rx_data 0xA5
    dut.rx_data.value = 0xA5
    dut.rx_valid.value = 1
    await RisingEdge(dut.clk)
    dut.rx_valid.value = 0

    value, _ = await bus.read(ISR_ADDR)
    assert value & 0b0010, f"RX_READY should be set, ISR={value:#06b}"

    first, _ = await bus.read(RDR_ADDR)
    assert first == 0xA5, f"first RDR read should return 0xA5, got {first:#x}"

    second, _ = await bus.read(RDR_ADDR)
    assert second == 0x00, f"second RDR read should return 0x00, got {second:#x}"

    value, _ = await bus.read(ISR_ADDR)
    assert value & 0b0010 == 0, f"RX_READY should be cleared by the RDR read, ISR={value:#06b}"


@cocotb.test()
async def test_seed_determinism(dut):
    """Same seed gives the same hw_log, reset reseeds, a different seed differs, no seed draws nothing."""
    bus = BusDriver(dut, seed=7)
    await bus.start()
    await bus.idle(64)
    log1 = list(bus.hw_log)
    assert len(log1) == 64, f"expected 64 log entries, got {len(log1)}"
    assert [cycle for cycle, _ in log1] == list(range(1, 65)), "log cycles should be 1..64"
    assert any(value != 0 for _, value in log1), "seeded run should draw at least one nonzero hw_set"

    await bus.reset()
    await bus.idle(64)
    assert bus.hw_log == log1, "reset should reseed so the same seed replays the same hw_log"

    other = BusDriver(dut, seed=8)
    await other.reset()
    await other.idle(64)
    assert other.hw_log != log1, "a different seed should give a different hw_log"

    plain = BusDriver(dut)
    await plain.reset()
    await plain.idle(5)
    assert plain.hw_log == [], f"unseeded driver should log nothing, got {plain.hw_log}"
    assert int(dut.hw_set.value) == 0, "unseeded driver should keep hw_set at 0"


@cocotb.test()
async def test_peek_does_not_clear_rdr(dut):
    """peek() leaves re low and does not clear UART_RDR, even across a rising edge."""
    bus = BusDriver(dut)
    await bus.start()

    # Load UART_RDR with 0xA5: rx_valid high for exactly one rising edge
    dut.rx_data.value = 0xA5
    dut.rx_valid.value = 1
    await RisingEdge(dut.clk)
    dut.rx_valid.value = 0

    first = await bus.peek(RDR_ADDR)
    assert first == 0xA5, f"peek should return the loaded UART_RDR, got {first:#x}"
    assert int(dut.re.value) == 0, f"peek must not assert the read strobe, re={int(dut.re.value)}"

    await RisingEdge(dut.clk)
    assert int(dut.re.value) == 0, "re must stay low across a rising edge after peek"

    second = await bus.peek(RDR_ADDR)
    assert second == 0xA5, f"peek must not clear UART_RDR; after a rising edge got {second:#x}"
