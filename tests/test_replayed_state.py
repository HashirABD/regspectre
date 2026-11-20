"""Unit tests for engine/replayed_state.py.

Pure Python. These tests need no simulator and do not import cocotb.
"""

import pytest

from engine.replayed_state import (
    isr_replayed_state,
    make_replayed_state,
    rdr_replayed_state,
    validate_replayed_state,
)


def test_isr_empty_accesses_gives_none():
    assert isr_replayed_state([]) is None


def test_isr_reads_only_gives_none():
    accesses = [{"kind": "READ", "pre": 9, "post": 9}]
    assert isr_replayed_state(accesses) is None


def test_isr_single_write_gives_pre_and_post():
    accesses = [{"kind": "WRITE", "pre": 9, "post": 0}]
    assert isr_replayed_state(accesses) == {"register": "UART_ISR", "pre": 9, "post": 0}


def test_isr_read_then_write_takes_pre_from_read():
    accesses = [
        {"kind": "READ", "pre": 5, "post": 5},
        {"kind": "WRITE", "pre": 5, "post": 8},
    ]
    assert isr_replayed_state(accesses) == {"register": "UART_ISR", "pre": 5, "post": 8}


def test_isr_rmw_gives_pre_and_post():
    accesses = [{"kind": "RMW", "pre": 9, "post": 0}]
    assert isr_replayed_state(accesses) == {"register": "UART_ISR", "pre": 9, "post": 0}


def test_isr_read_then_rmw_takes_pre_from_read():
    accesses = [
        {"kind": "READ", "pre": 9, "post": 9},
        {"kind": "RMW", "pre": 9, "post": 0},
    ]
    assert isr_replayed_state(accesses) == {"register": "UART_ISR", "pre": 9, "post": 0}


def test_rdr_returns_state_and_is_never_none():
    state = rdr_replayed_state(165, 0)
    assert state == {"register": "UART_RDR", "pre": 165, "post": 0}
    assert state is not None


def test_make_returns_dict():
    assert make_replayed_state("UART_ISR", 9, 0) == {"register": "UART_ISR", "pre": 9, "post": 0}


def test_make_rejects_unknown_register():
    with pytest.raises(ValueError):
        make_replayed_state("UART_TX", 0, 0)


def test_make_rejects_negative_values():
    with pytest.raises(ValueError):
        make_replayed_state("UART_ISR", -1, 0)
    with pytest.raises(ValueError):
        make_replayed_state("UART_RDR", 0, -1)


def test_validate_rejects_bool_pre():
    with pytest.raises(ValueError):
        validate_replayed_state({"register": "UART_ISR", "pre": True, "post": 0})
    with pytest.raises(ValueError):
        validate_replayed_state({"register": "UART_ISR", "pre": False, "post": 0})


def test_validate_rejects_bool_post():
    with pytest.raises(ValueError):
        validate_replayed_state({"register": "UART_RDR", "pre": 0, "post": True})
    with pytest.raises(ValueError):
        validate_replayed_state({"register": "UART_RDR", "pre": 0, "post": False})


def test_validate_rejects_isr_pre_above_max():
    with pytest.raises(ValueError):
        validate_replayed_state({"register": "UART_ISR", "pre": 16, "post": 0})


def test_validate_rejects_rdr_post_above_max():
    with pytest.raises(ValueError):
        validate_replayed_state({"register": "UART_RDR", "pre": 0, "post": 256})


def test_validate_accepts_none():
    assert validate_replayed_state(None) is None


def test_validate_rejects_missing_key():
    with pytest.raises(ValueError):
        validate_replayed_state({"register": "UART_ISR", "pre": 9})


def test_validate_rejects_extra_key():
    with pytest.raises(ValueError):
        validate_replayed_state({"register": "UART_ISR", "pre": 9, "post": 0, "extra": 1})


def test_validate_accepts_boundary_values():
    assert validate_replayed_state({"register": "UART_ISR", "pre": 15, "post": 0}) is None
    assert validate_replayed_state({"register": "UART_RDR", "pre": 0, "post": 255}) is None
