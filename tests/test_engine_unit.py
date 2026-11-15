"""Unit tests for engine components."""

import pytest

from engine.regmap import (
    REGISTERS,
    ISR_ADDR,
    RDR_ADDR,
    addr_to_name,
    bit_name_to_index,
    bit_type,
)


def test_regmap_isr_address():
    assert REGISTERS["UART_ISR"]["addr"] == ISR_ADDR == 0x40001004


def test_regmap_rdr_address():
    assert REGISTERS["UART_RDR"]["addr"] == RDR_ADDR == 0x40001008


def test_regmap_isr_width():
    assert REGISTERS["UART_ISR"]["width"] == 4


def test_regmap_rdr_width():
    assert REGISTERS["UART_RDR"]["width"] == 8


def test_regmap_isr_bit_definitions():
    bits = REGISTERS["UART_ISR"]["bits"]
    assert bits[0] == ("TX_DONE", "W1C")
    assert bits[1] == ("RX_READY", "RO")
    assert bits[2] == ("PARITY_ERR", "W1C")
    assert bits[3] == ("OVERRUN_ERR", "W1C")


def test_regmap_rdr_bit_definitions():
    bits = REGISTERS["UART_RDR"]["bits"]
    assert len(bits) == 8
    for i in range(8):
        assert bits[i] == (f"RDR[{i}]", "RTC")


def test_regmap_addr_to_name_known():
    assert addr_to_name(ISR_ADDR) == "UART_ISR"
    assert addr_to_name(RDR_ADDR) == "UART_RDR"


def test_regmap_addr_to_name_unknown():
    with pytest.raises(KeyError):
        addr_to_name(0x40001000)


def test_regmap_bit_name_to_index_isr():
    assert bit_name_to_index("UART_ISR", "TX_DONE") == 0
    assert bit_name_to_index("UART_ISR", "RX_READY") == 1
    assert bit_name_to_index("UART_ISR", "PARITY_ERR") == 2
    assert bit_name_to_index("UART_ISR", "OVERRUN_ERR") == 3


def test_regmap_bit_name_to_index_rdr():
    assert bit_name_to_index("UART_RDR", "RDR[0]") == 0
    assert bit_name_to_index("UART_RDR", "RDR[7]") == 7


def test_regmap_bit_name_to_index_unknown():
    with pytest.raises(KeyError):
        bit_name_to_index("UART_ISR", "NONEXISTENT")


def test_regmap_bit_type_isr():
    assert bit_type("UART_ISR", 0) == "W1C"
    assert bit_type("UART_ISR", 1) == "RO"
    assert bit_type("UART_ISR", 2) == "W1C"
    assert bit_type("UART_ISR", 3) == "W1C"


def test_regmap_bit_type_rdr():
    for i in range(8):
        assert bit_type("UART_RDR", i) == "RTC"