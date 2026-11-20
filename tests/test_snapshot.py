"""Tests for engine/snapshot.py: schema, validation, atomic write, and the literal check.

Pure pytest. This module does not import cocotb and needs no simulator.
"""

import json

import pytest

from engine import snapshot as snapshot_module
from engine.snapshot import REPO_ROOT, SNAPSHOT_PATH, build_snapshot, write_snapshot_atomic
from engine.snippets import DEMO_SNIPPET_NAMES

CREATED = "2026-11-15T12:00:00Z"
# Built at runtime, so this file does not contain the literal that the literal check scans for.
SNAPSHOT_LITERAL = "demo_" + "snapshot.json"
RECORD_KEYS = ["name", "source", "report", "replayed_state"]


def _valid_records():
    """Four records in DEMO_SNIPPET_NAMES order, with two null states, one UART_ISR state and one UART_RDR state."""
    states = [
        {"register": "UART_ISR", "pre": 9, "post": 0},
        None,
        None,
        {"register": "UART_RDR", "pre": 65, "post": 0},
    ]
    return [
        {"name": name, "source": "void h(void) {}\n", "report": "[]", "replayed_state": state}
        for name, state in zip(DEMO_SNIPPET_NAMES, states)
    ]


def test_build_snapshot_has_exact_keys_and_record_order():
    payload = build_snapshot(_valid_records(), CREATED)
    assert list(payload) == ["created_utc", "records"]
    assert payload["created_utc"] == CREATED
    assert [record["name"] for record in payload["records"]] == list(DEMO_SNIPPET_NAMES)
    for record in payload["records"]:
        assert list(record) == RECORD_KEYS
    assert payload["records"][0]["replayed_state"] == {"register": "UART_ISR", "pre": 9, "post": 0}
    assert payload["records"][1]["replayed_state"] is None


def test_build_snapshot_rejects_swapped_names():
    records = _valid_records()
    records[0], records[1] = records[1], records[0]
    with pytest.raises(ValueError):
        build_snapshot(records, CREATED)


def test_build_snapshot_rejects_unknown_name():
    records = _valid_records()
    records[2]["name"] = "NOT_A_SNIPPET"
    with pytest.raises(ValueError):
        build_snapshot(records, CREATED)


def test_build_snapshot_rejects_wrong_record_count():
    records = _valid_records()
    with pytest.raises(ValueError):
        build_snapshot(records[:3], CREATED)
    with pytest.raises(ValueError):
        build_snapshot(records + [dict(records[0])], CREATED)


def test_build_snapshot_rejects_missing_record_key():
    records = _valid_records()
    del records[1]["source"]
    with pytest.raises(ValueError):
        build_snapshot(records, CREATED)


def test_build_snapshot_rejects_extra_record_key():
    records = _valid_records()
    records[1]["extra"] = 1
    with pytest.raises(ValueError):
        build_snapshot(records, CREATED)


@pytest.mark.parametrize("bad_source", [None, 5, b"void h(void) {}"])
def test_build_snapshot_rejects_non_str_source(bad_source):
    records = _valid_records()
    records[0]["source"] = bad_source
    with pytest.raises(ValueError):
        build_snapshot(records, CREATED)


@pytest.mark.parametrize("bad_report", ["not json", "{}", "[1]", '[{}, "x"]', 5])
def test_build_snapshot_rejects_bad_report(bad_report):
    records = _valid_records()
    records[0]["report"] = bad_report
    with pytest.raises(ValueError):
        build_snapshot(records, CREATED)


@pytest.mark.parametrize(
    "bad_state",
    [
        {"register": "UART_ISR", "pre": True, "post": 0},
        {"register": "UART_ISR", "pre": 16, "post": 0},
        {"register": "UART_ISR", "pre": 9},
        "UART_ISR",
    ],
)
def test_build_snapshot_rejects_invalid_replayed_state_and_names_the_record(bad_state):
    records = _valid_records()
    records[0]["replayed_state"] = bad_state
    with pytest.raises(ValueError, match=DEMO_SNIPPET_NAMES[0]):
        build_snapshot(records, CREATED)


@pytest.mark.parametrize(
    "bad_time",
    ["2026-11-15 12:00:00", "2026-11-15T12:00:00", "2026-11-15T12:00:00Z\n", "2026-11-15T12:00:00+00:00", None],
)
def test_build_snapshot_rejects_bad_created_utc(bad_time):
    with pytest.raises(ValueError):
        build_snapshot(_valid_records(), bad_time)


def test_write_snapshot_atomic_writes_exact_text(tmp_path):
    target = tmp_path / "web" / "public" / "x.json"
    payload = build_snapshot(_valid_records(), CREATED)
    assert not target.parent.exists()

    write_snapshot_atomic(target, payload)

    data = target.read_bytes()
    assert data == (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    assert b"\r" not in data
    assert not target.with_name("x.json.tmp").exists()


def test_failed_replace_keeps_old_bytes_and_removes_tmp(tmp_path, monkeypatch):
    target = tmp_path / "x.json"
    target.write_bytes(b"old\n")
    payload = build_snapshot(_valid_records(), CREATED)

    def failing_replace(src, dst):
        raise OSError("boom")

    monkeypatch.setattr(snapshot_module.os, "replace", failing_replace)
    with pytest.raises(OSError):
        write_snapshot_atomic(target, payload)

    assert target.read_bytes() == b"old\n"
    assert not target.with_name("x.json.tmp").exists()


def test_invalid_records_leave_existing_file_untouched(tmp_path):
    target = tmp_path / "x.json"
    target.write_bytes(b"old\n")
    records = _valid_records()
    records[0]["report"] = "{}"

    with pytest.raises(ValueError):
        build_snapshot(records, CREATED)

    assert target.read_bytes() == b"old\n"
    assert not target.with_name("x.json.tmp").exists()


def test_invalid_records_leave_missing_file_missing(tmp_path):
    target = tmp_path / "never" / "x.json"
    records = _valid_records()
    records[3]["replayed_state"] = {"register": "UART_RDR", "pre": 256, "post": 0}

    with pytest.raises(ValueError):
        build_snapshot(records, CREATED)

    assert not target.exists()
    assert not target.parent.exists()


def _files_containing_literal():
    scans = [
        (REPO_ROOT / "engine", "*.py"),
        (REPO_ROOT / "backend", "*.py"),
        (REPO_ROOT / "tests", "*.py"),
        (REPO_ROOT / "web" / "lib", "*.ts"),
    ]
    found = set()
    for folder, pattern in scans:
        if not folder.is_dir():
            continue
        for path in folder.rglob(pattern):
            if SNAPSHOT_LITERAL in path.read_text(encoding="utf-8"):
                found.add(path.relative_to(REPO_ROOT))
    return found


def test_literal_appears_only_in_engine_snapshot_module():
    expected = {(REPO_ROOT / "engine" / "snapshot.py").relative_to(REPO_ROOT)}
    assert _files_containing_literal() == expected


def test_snapshot_path_uses_the_expected_name():
    assert SNAPSHOT_PATH.name == SNAPSHOT_LITERAL
    assert SNAPSHOT_PATH == REPO_ROOT / "web" / "public" / SNAPSHOT_LITERAL
