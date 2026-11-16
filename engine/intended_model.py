"""Intended_State model for one firmware operation.

intended_state(op, pre) returns the register value the firmware operation was
expected to produce. The value is an int with one bit per register bit, where
bit 0 is the least significant. pre is the register value before the operation.

For an operation that names bit mask M and writes value W:
- Bits outside M keep their pre value.
- Bits inside M of type W1C: 0 if W has the bit set, else pre (write-0 is a no-op).
- Bits inside M of type RO or RTC: pre. Writes to these bits have no effect.

Direct assignment (WRITE): M is the written value, so W = M.
RMW SET (|=): W = pre | M.
RMW CLR (&= ~M): W = pre & ~M.
READ names no bits. Only read-to-clear (RTC) bits change, and they become 0,
because the firmware read is meant to consume them. Other bits keep pre.
"""

from engine.c_parser import KIND_READ, KIND_RMW, KIND_WRITE, MODE_CLR, MODE_SET
from engine.regmap import REGISTERS, bit_type

W1C = "W1C"
RTC = "RTC"


def _written_value(op, pre, full):
    if op.kind == KIND_WRITE:
        return op.mask & full
    if op.kind == KIND_RMW and op.mode == MODE_SET:
        return (pre | op.mask) & full
    if op.kind == KIND_RMW and op.mode == MODE_CLR:
        return (pre & ~op.mask) & full
    raise ValueError(f"no written value for kind {op.kind!r} mode {op.mode!r}")


def intended_state(op, pre):
    """Return the Intended_State of op applied to the pre-operation value pre."""
    width = REGISTERS[op.reg]["width"]
    full = (1 << width) - 1
    if not 0 <= pre <= full:
        raise ValueError(f"pre {pre:#x} does not fit in {width} bits of {op.reg}")

    if op.kind == KIND_READ:
        result = pre
        for i in range(width):
            if bit_type(op.reg, i) == RTC:
                result &= ~(1 << i)
        return result

    written = _written_value(op, pre, full)
    named = op.mask & full
    result = pre
    for i in range(width):
        if (named >> i) & 1 and bit_type(op.reg, i) == W1C and (written >> i) & 1:
            result &= ~(1 << i)
    return result