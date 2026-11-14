import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


@cocotb.test()
async def rmw_wipes_neighbor_interrupt(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst_n.value = 0
    dut.we.value = 0
    dut.wdata.value = 0
    dut.hw_set.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    dut.hw_set.value = 0b1001
    await RisingEdge(dut.clk)
    dut.hw_set.value = 0
    await RisingEdge(dut.clk)
    old = int(dut.status.value)
    assert old == 0b1001, f"setup failed, status={old:#06b}"

    dut.wdata.value = old | 0b0001
    dut.we.value = 1
    await RisingEdge(dut.clk)
    dut.we.value = 0
    await RisingEdge(dut.clk)
    after = int(dut.status.value)

    intended = old & ~0b0001
    corrupted = intended & ~after & 0xFFFFFFFF
    dut._log.info(f"intended={intended:#06b} actual={after:#06b} corrupted={corrupted:#06b}")
    assert corrupted == 0b1000, "RegSpectre did not catch the neighbor bit wipeout"
