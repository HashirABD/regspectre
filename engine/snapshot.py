"""Snapshot schema, validator, and atomic writer for the demo run.

The Snapshot is written only by the demo run path, python3 -m engine.demo run.
build_snapshot checks a payload and never touches the disk. write_snapshot_atomic
is the only function in this module that writes a file.

Pure Python. This module does not import cocotb.
"""

import json
import os
import re
from pathlib import Path

from engine.replayed_state import validate_replayed_state
from engine.snippets import DEMO_SNIPPET_NAMES

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = REPO_ROOT / "web" / "public" / "demo_snapshot.json"

_RECORD_KEYS = frozenset({"name", "source", "report", "replayed_state"})
_CREATED_UTC_PATTERN = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"


def _check_record(index, record, expected_name):
    if not isinstance(record, dict):
        raise ValueError(f"record {index} must be a dict, got {type(record).__name__}")
    if set(record.keys()) != _RECORD_KEYS:
        raise ValueError(
            f"record {index} must have exactly the keys {sorted(_RECORD_KEYS)}, "
            f"got {sorted(record.keys(), key=str)}"
        )
    if record["name"] != expected_name:
        raise ValueError(
            f"record {index} must be named {expected_name!r}, got {record['name']!r}"
        )

    source = record["source"]
    if not isinstance(source, str):
        raise ValueError(f"{expected_name}: source must be a str, got {type(source).__name__}")

    report = record["report"]
    if not isinstance(report, str):
        raise ValueError(f"{expected_name}: report must be a str, got {type(report).__name__}")
    try:
        parsed = json.loads(report)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{expected_name}: report is not valid JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise ValueError(
            f"{expected_name}: report must be a JSON list, got {type(parsed).__name__}"
        )
    for item in parsed:
        if not isinstance(item, dict):
            raise ValueError(
                f"{expected_name}: every report entry must be a JSON object, "
                f"got {type(item).__name__}"
            )

    try:
        validate_replayed_state(record["replayed_state"])
    except ValueError as exc:
        raise ValueError(f"{expected_name}: {exc}") from exc


def build_snapshot(records, created_utc):
    if not isinstance(records, list) or len(records) != len(DEMO_SNIPPET_NAMES):
        raise ValueError(f"records must be a list of {len(DEMO_SNIPPET_NAMES)} entries")
    for index, (record, expected_name) in enumerate(zip(records, DEMO_SNIPPET_NAMES)):
        _check_record(index, record, expected_name)
    if not isinstance(created_utc, str) or re.fullmatch(
        _CREATED_UTC_PATTERN, created_utc, re.ASCII
    ) is None:
        raise ValueError(f"created_utc must match YYYY-MM-DDTHH:MM:SSZ, got {created_utc!r}")
    return {
        "created_utc": created_utc,
        "records": [
            {
                "name": record["name"],
                "source": record["source"],
                "report": record["report"],
                "replayed_state": record["replayed_state"],
            }
            for record in records
        ],
    }


def write_snapshot_atomic(path, payload):
    text = json.dumps(payload, indent=2) + "\n"
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            # A cleanup failure must not hide the original error.
            pass
        raise
