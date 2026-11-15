"""Register map for the UART co verification core.

Single source of register and bit metadata for the parser, intended model,
detector, and report writer.
"""

ISR_ADDR = 0x40001004
RDR_ADDR = 0x40001008

REGISTERS = {
    "UART_ISR": {
        "addr": ISR_ADDR,
        "width": 4,
        "bits": {
            0: ("TX_DONE", "W1C"),
            1: ("RX_READY", "RO"),
            2: ("PARITY_ERR", "W1C"),
            3: ("OVERRUN_ERR", "W1C"),
        },
    },
    "UART_RDR": {
        "addr": RDR_ADDR,
        "width": 8,
        "bits": {i: (f"RDR[{i}]", "RTC") for i in range(8)},
    },
}


def addr_to_name(addr):
    """Look up a register name by its bus address."""
    for name, info in REGISTERS.items():
        if info["addr"] == addr:
            return name
    raise KeyError(f"no register at address {addr:#010x}")


def bit_name_to_index(reg_name, bit_name):
    """Look up a bit index by register name and bit name."""
    bits = REGISTERS[reg_name]["bits"]
    for idx, (name, _) in bits.items():
        if name == bit_name:
            return idx
    raise KeyError(f"no bit named {bit_name!r} in register {reg_name}")


def bit_type(reg_name, bit_index):
    """Query the type of a bit (W1C, RO, or RTC) by register name and index."""
    return REGISTERS[reg_name]["bits"][bit_index][1]
