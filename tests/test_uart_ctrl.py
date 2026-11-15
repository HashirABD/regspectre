import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

ISR_ADDR = 0x40001004
RDR_ADDR = 0x40001008


async def init(dut):
    """Start clock and reset the DUT."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst_n.value = 0
    dut.we.value = 0
    dut.re.value = 0
    dut.addr.value = 0
    dut.wdata.value = 0
    dut.hw_set.value = 0
    dut.rx_valid.value = 0
    dut.rx_data.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def bus_write(dut, addr, data):
    """Write data to addr. Commits on the rising edge."""
    dut.we.value = 1
    dut.re.value = 0
    dut.addr.value = addr
    dut.wdata.value = data
    await RisingEdge(dut.clk)
    dut.we.value = 0
    await RisingEdge(dut.clk)


async def read_reg(dut, addr):
    """Combinational read without side effects (re stays 0)."""
    dut.we.value = 0
    dut.re.value = 0
    dut.addr.value = addr
    await Timer(1, "ns")
    return int(dut.rdata.value)


async def read_rdr(dut):
    """Read RDR: returns old value, then clears RDR and RX_READY at the edge."""
    dut.we.value = 0
    dut.re.value = 1
    dut.addr.value = RDR_ADDR
    await Timer(1, "ns")
    value = int(dut.rdata.value) & 0xFF
    await RisingEdge(dut.clk)
    dut.re.value = 0
    await Timer(1, "ns")
    return value


@cocotb.test()
async def test_address_decode(dut):
    """Req 1.1: ISR at 0x40001004, RDR at 0x40001008, unknown addr returns 0."""
    await init(dut)

    # Set ISR bits via hw_set
    dut.hw_set.value = 0b1101
    await RisingEdge(dut.clk)
    dut.hw_set.value = 0
    await RisingEdge(dut.clk)

    # ISR at correct address
    isr_val = await read_reg(dut, ISR_ADDR)
    assert isr_val & 0xF == 0b1101, f"ISR read failed: got {isr_val & 0xF:#06b}"

    # Load RDR via rx_valid
    dut.rx_valid.value = 1
    dut.rx_data.value = 0xAB
    await RisingEdge(dut.clk)
    dut.rx_valid.value = 0
    await RisingEdge(dut.clk)

    # RDR at correct address
    rdr_val = await read_reg(dut, RDR_ADDR)
    assert (rdr_val & 0xFF) == 0xAB, f"RDR read failed: got {rdr_val & 0xFF:#x}"

    # Unknown address returns 0
    unknown = await read_reg(dut, 0x40001000)
    assert unknown == 0, f"Unknown addr should return 0, got {unknown:#x}"


@cocotb.test()
async def test_w1c_clear_on_write_one(dut):
    """Req 1.2: Writing 1 to a W1C bit clears it."""
    await init(dut)

    dut.hw_set.value = 0b0101  # bits 0 and 2
    await RisingEdge(dut.clk)
    dut.hw_set.value = 0
    await RisingEdge(dut.clk)

    # Write 1 to bit 0 (clear TX_DONE)
    await bus_write(dut, ISR_ADDR, 1 << 0)

    isr_val = await read_reg(dut, ISR_ADDR)
    assert isr_val & 0xF == 0b0100, f"Expected 0b0100, got {isr_val & 0xF:#06b}"


@cocotb.test()
async def test_hw_set_sets_bit(dut):
    """Req 1.3: hw_set asserts an interrupt bit."""
    await init(dut)

    dut.hw_set.value = 0b1101  # bits 0, 2, 3 (bit 1 is RX_READY, set by rx_valid)
    await RisingEdge(dut.clk)
    dut.hw_set.value = 0
    await RisingEdge(dut.clk)

    isr_val = await read_reg(dut, ISR_ADDR)
    assert isr_val & 0xF == 0b1101, f"Expected 0b1101, got {isr_val & 0xF:#06b}"


@cocotb.test()
async def test_write_zero_no_op(dut):
    """Req 1.4: Writing 0 to a W1C bit leaves it unchanged."""
    await init(dut)

    dut.hw_set.value = 0b0101  # bits 0 and 2
    await RisingEdge(dut.clk)
    dut.hw_set.value = 0
    await RisingEdge(dut.clk)

    # Write 0 (no bits to clear)
    await bus_write(dut, ISR_ADDR, 0)

    isr_val = await read_reg(dut, ISR_ADDR)
    assert isr_val & 0xF == 0b0101, f"Expected 0b0101, got {isr_val & 0xF:#06b}"


@cocotb.test()
async def test_reset_zeroes(dut):
    """Req 1.5: Reset zeroes UART_ISR and UART_RDR."""
    await init(dut)

    # Set ISR bits
    dut.hw_set.value = 0b1101
    await RisingEdge(dut.clk)
    dut.hw_set.value = 0
    await RisingEdge(dut.clk)

    # Load RDR
    dut.rx_valid.value = 1
    dut.rx_data.value = 0xFF
    await RisingEdge(dut.clk)
    dut.rx_valid.value = 0
    await RisingEdge(dut.clk)

    # Assert reset
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    isr_val = await read_reg(dut, ISR_ADDR)
    assert isr_val & 0xF == 0, f"ISR not zero after reset: {isr_val & 0xF:#06b}"

    rdr_val = await read_reg(dut, RDR_ADDR)
    assert rdr_val & 0xFF == 0, f"RDR not zero after reset: {rdr_val & 0xFF:#x}"


@cocotb.test()
async def test_rx_valid_loads_rdr(dut):
    """Req 1.6: rx_valid loads UART_RDR with rx_data and sets RX_READY."""
    await init(dut)

    dut.rx_valid.value = 1
    dut.rx_data.value = 0x5A
    await RisingEdge(dut.clk)
    dut.rx_valid.value = 0
    await RisingEdge(dut.clk)

    rdr_val = await read_reg(dut, RDR_ADDR)
    assert rdr_val & 0xFF == 0x5A, f"RDR should be 0x5A, got {rdr_val & 0xFF:#x}"

    isr_val = await read_reg(dut, ISR_ADDR)
    assert isr_val & 0x2 == 0x2, f"RX_READY should be set, ISR={isr_val & 0xF:#06b}"


@cocotb.test()
async def test_hw_set_wins_over_w1c(dut):
    """Req 1.7: hw_set and W1C clear on same bit in same cycle: bit stays set."""
    await init(dut)

    # Same cycle: hw_set[0]=1 and write 1 to bit 0 (W1C clear)
    dut.hw_set.value = 0b0001
    dut.we.value = 1
    dut.re.value = 0
    dut.addr.value = ISR_ADDR
    dut.wdata.value = 1 << 0
    await RisingEdge(dut.clk)
    dut.hw_set.value = 0
    dut.we.value = 0
    await RisingEdge(dut.clk)

    isr_val = await read_reg(dut, ISR_ADDR)
    assert isr_val & 0x1 == 0x1, f"Bit 0 should be set (hw_set wins), ISR={isr_val & 0xF:#06b}"


@cocotb.test()
async def test_write_rx_ready_ignored(dut):
    """Req 1.8: Writing to RX_READY (bit 1) is ignored."""
    await init(dut)

    # Set RX_READY via rx_valid
    dut.rx_valid.value = 1
    dut.rx_data.value = 0x00
    await RisingEdge(dut.clk)
    dut.rx_valid.value = 0
    await RisingEdge(dut.clk)

    # Write 0xFF to ISR (tries to clear all bits)
    await bus_write(dut, ISR_ADDR, 0xFF)

    isr_val = await read_reg(dut, ISR_ADDR)
    assert isr_val & 0x2 == 0x2, f"RX_READY should survive, ISR={isr_val & 0xF:#06b}"


@cocotb.test()
async def test_rdr_read_to_clear(dut):
    """Req 2.1: Reading RDR returns old value, then clears RDR and RX_READY."""
    await init(dut)

    # Load RDR with 0x3C
    dut.rx_valid.value = 1
    dut.rx_data.value = 0x3C
    await RisingEdge(dut.clk)
    dut.rx_valid.value = 0
    await RisingEdge(dut.clk)

    # First read: should return 0x3C
    val = await read_rdr(dut)
    assert val == 0x3C, f"First RDR read should return 0x3C, got {val:#x}"

    # RX_READY should be cleared
    isr_val = await read_reg(dut, ISR_ADDR)
    assert isr_val & 0x2 == 0, f"RX_READY should be cleared, ISR={isr_val & 0xF:#06b}"

    # Second read: should return 0 (RDR cleared)
    val2 = await read_rdr(dut)
    assert val2 == 0, f"Second RDR read should return 0, got {val2:#x}"