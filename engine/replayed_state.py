"""Replayed_State builders and validator for the UART_ISR and UART_RDR replays.

Pure Python. This module imports nothing and needs no simulator.

A Replayed_State is the JSON object {"register": ..., "pre": int, "post": int}, or null.
The register is UART_ISR or UART_RDR. Integer ranges: UART_ISR 0 to 15, UART_RDR 0 to 255.
"""

REGISTER_MAX = {"UART_ISR": 15, "UART_RDR": 255}

_KEYS = frozenset({"register", "pre", "post"})


def _check_value(name, value, maximum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an int, not a bool or other type: {value!r}")
    if not 0 <= value <= maximum:
        raise ValueError(f"{name} must be from 0 to {maximum}, got {value}")


def make_replayed_state(register, pre, post):
    if not isinstance(register, str) or register not in REGISTER_MAX:
        raise ValueError(f"register must be one of {sorted(REGISTER_MAX)}, got {register!r}")
    maximum = REGISTER_MAX[register]
    _check_value("pre", pre, maximum)
    _check_value("post", post, maximum)
    return {"register": register, "pre": pre, "post": post}


def validate_replayed_state(value):
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"Replayed_State must be a dict or None, got {type(value).__name__}")
    if set(value.keys()) != _KEYS:
        raise ValueError(f"Replayed_State must have exactly the keys {sorted(_KEYS)}, got {sorted(value.keys())}")
    make_replayed_state(value["register"], value["pre"], value["post"])
    return None


def isr_replayed_state(accesses):
    if not any(access["kind"] in ("WRITE", "RMW") for access in accesses):
        return None
    return make_replayed_state("UART_ISR", accesses[0]["pre"], accesses[-1]["post"])


def rdr_replayed_state(pre, post):
    return make_replayed_state("UART_RDR", pre, post)
