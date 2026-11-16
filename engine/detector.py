"""Violation detector for UART_ISR read-modify-write operations.

detect_violations compares the Intended_State from intended_state(op, pre) with
an Actual_State read from the RTL. For a read-modify-write on UART_ISR it returns
one Violation_Report for each W1C bit where Intended_State is 1 and Actual_State is 0.
A bit that should have stayed set but was cleared is the loss pattern.

Only W1C bits are reported. RX_READY (bit 1) is read only and hardware controlled,
so it never produces a report. The W1C bit list comes from engine/regmap.py.

Every other operation returns an empty list. That includes direct assignments
and plain READs. Read-to-clear double-read detection is not in this module.
"""

from dataclasses import dataclass

from engine.c_parser import KIND_RMW
from engine.intended_model import intended_state
from engine.regmap import REGISTERS, bit_type

_ISR_WIDTH = REGISTERS["UART_ISR"]["width"]
_ISR_W1C_BITS = tuple(
    bit for bit in range(_ISR_WIDTH) if bit_type("UART_ISR", bit) == "W1C"
)


@dataclass
class Violation_Report:
    register: str
    bit: int
    intended: int
    actual: int
    cycle: int
    c_line: int | None = None


def detect_violations(op, pre, actual, cycle):
    """Return one Violation_Report per W1C bit that was intended set and is actually clear.

    op is an Operation, pre is the UART_ISR value before op, actual is the
    UART_ISR value read from the RTL after op, and cycle is the commit cycle of op.
    c_line is copied from op. It is None for raw transaction lists.
    """
    if op.kind != KIND_RMW or op.reg != "UART_ISR":
        return []

    full = (1 << _ISR_WIDTH) - 1
    if not 0 <= actual <= full:
        raise ValueError(f"actual {actual:#x} does not fit in {_ISR_WIDTH} bits of UART_ISR")
    if cycle < 0:
        raise ValueError(f"cycle must be >= 0, got {cycle}")

    intended = intended_state(op, pre)
    reports = []
    for bit in _ISR_W1C_BITS:
        if ((intended >> bit) & 1) == 1 and ((actual >> bit) & 1) == 0:
            reports.append(
                Violation_Report(
                    register=op.reg,
                    bit=bit,
                    intended=1,
                    actual=0,
                    cycle=cycle,
                    c_line=op.c_line,
                )
            )
    return reports