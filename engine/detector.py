"""Violation detector for UART_ISR and UART_RDR.

detect_violations compares the Intended_State from intended_state(op, pre) with
an Actual_State read from the RTL. For a read-modify-write on UART_ISR it returns
one Violation_Report for each W1C bit where Intended_State is 1 and Actual_State is 0.
A bit that should have stayed set but was cleared is the loss pattern.

Only W1C bits are reported. RX_READY (bit 1) is read only and hardware controlled,
so it never produces a report. The W1C bit list comes from engine/regmap.py.

detect_rdr_double_reads checks UART_RDR reads inside one Interrupt_Handler. In each
handler the second UART_RDR read is compared with the first. Each bit that was 1
in the first read and 0 in the second read is reported. Reads of other registers
and reads outside any handler are ignored.

detect_violations returns an empty list for every operation other than a
read-modify-write on UART_ISR. That includes direct assignments and plain READs.
"""

from dataclasses import dataclass

from engine.c_parser import KIND_READ, KIND_RMW
from engine.intended_model import intended_state
from engine.regmap import REGISTERS, bit_type

_ISR_WIDTH = REGISTERS["UART_ISR"]["width"]
_ISR_W1C_BITS = tuple(
    bit for bit in range(_ISR_WIDTH) if bit_type("UART_ISR", bit) == "W1C"
)

_RDR_WIDTH = REGISTERS["UART_RDR"]["width"]
_RDR_RTC_BITS = tuple(
    bit for bit in range(_RDR_WIDTH) if bit_type("UART_RDR", bit) == "RTC"
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


def detect_rdr_double_reads(reads):
    """Return the Violation_Reports for second UART_RDR reads inside each handler.

    reads is a sequence of (op, value, cycle) tuples in program order, one for
    each read operation the firmware performed:
    - op is an Operation. Only READ operations on UART_RDR are used.
    - value is the 8-bit rdata the RTL returned for that read.
    - cycle is the commit cycle of that read.

    Reads are grouped by op.handler. Reads with an empty handler are not inside
    an Interrupt_Handler and are ignored. In each handler the first UART_RDR read
    is the baseline. The second is compared with it, and reads after the second
    are not compared.

    For each read-to-clear bit that was 1 in the first value and 0 in the second,
    the report has register UART_RDR, intended 1, actual 0, the second read's
    cycle, and the second read's c_line.
    """
    reports = []
    read_counts = {}
    first_values = {}
    for op, value, cycle in reads:
        if op.kind != KIND_READ or op.reg != "UART_RDR" or not op.handler:
            continue
        if not 0 <= value < (1 << _RDR_WIDTH):
            raise ValueError(f"value {value:#x} does not fit in {_RDR_WIDTH} bits of UART_RDR")
        if cycle < 0:
            raise ValueError(f"cycle must be >= 0, got {cycle}")

        count = read_counts.get(op.handler, 0) + 1
        read_counts[op.handler] = count
        if count == 1:
            first_values[op.handler] = value
        elif count == 2:
            first = first_values[op.handler]
            for bit in _RDR_RTC_BITS:
                if ((first >> bit) & 1) == 1 and ((value >> bit) & 1) == 0:
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