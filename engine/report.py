"""JSON report writer for Violation_Report records.

reports_to_json turns a list of Violation_Report objects into a JSON string.

Format rules:
- The top level is a JSON array of violation objects. There is no wrapper
  object and no summary count.
- Each object has the keys register, bit, intended, actual, cycle, c_line, in
  that order.
- Violations keep the order of the input list. The writer does not sort them.
- c_line is written only when it is not None. A raw transaction list has
  c_line None, so the key is left out. It is never written as null.
- Every field is type-checked before serializing.

The same input list always gives the same string.
"""

import json

from engine.detector import Violation_Report


def _check_int(name, value, minimum):
    if type(value) is not int:
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    return value


def _check_bit(name, value):
    if type(value) is not int:
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    if value not in (0, 1):
        raise ValueError(f"{name} must be 0 or 1, got {value}")
    return value


def report_to_dict(report):
    """Return one violation as a dict with keys in the fixed report order."""
    if not isinstance(report, Violation_Report):
        raise TypeError(f"expected Violation_Report, got {type(report).__name__}")
    if type(report.register) is not str:
        raise TypeError(f"register must be a str, got {type(report.register).__name__}")
    if not report.register:
        raise ValueError("register must not be empty")

    data = {
        "register": report.register,
        "bit": _check_int("bit", report.bit, 0),
        "intended": _check_bit("intended", report.intended),
        "actual": _check_bit("actual", report.actual),
        "cycle": _check_int("cycle", report.cycle, 0),
    }
    if report.c_line is not None:
        data["c_line"] = _check_int("c_line", report.c_line, 1)
    return data


def reports_to_json(reports):
    """Return the JSON array text for reports, in input order."""
    records = [report_to_dict(report) for report in reports]
    return json.dumps(records, indent=2)