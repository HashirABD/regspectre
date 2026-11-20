"""Tests for engine/sim_runner.py. A fake make command stands in for the simulator.

Pure pytest. This file imports no cocotb and never touches the real tests/.sim.lock.
"""

import fcntl
import os
import sys
import time
from pathlib import Path

import pytest

import engine.sim_runner as sim_runner

RUNS = [
    {"name": "A", "source": "void h(void) {}\n"},
    {"name": "B", "source": "void g(void) {}\n"},
]

RECORD_KEYS = {"name", "source", "report", "replayed_state"}

FAKE_MAKE = '''\
import json
import os
import subprocess
import sys
import time

mode = os.environ.get("FAKE_MODE", "ok")


def write_out(payload):
    with open(os.environ["REGSPECTRE_RUN_OUT"], "w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def echo_records():
    with open(os.environ["REGSPECTRE_RUN_IN"], encoding="utf-8") as handle:
        runs = json.load(handle)["runs"]
    return [
        {"name": run["name"], "source": run["source"], "report": "[]", "replayed_state": None}
        for run in runs
    ]


if mode == "ok":
    write_out({"records": echo_records()})
    sys.exit(0)
if mode == "fail":
    sys.stderr.write("first line\\nlast line\\n")
    sys.exit(2)
if mode == "hang":
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    with open(os.environ["FAKE_PID_FILE"], "w", encoding="utf-8") as handle:
        handle.write(str(child.pid))
    time.sleep(60)
    sys.exit(0)
if mode == "badout":
    write_out({"records": [{"name": "WRONG", "source": "x", "report": "[]", "replayed_state": None}]})
    sys.exit(0)
if mode == "noout":
    sys.exit(0)
sys.exit(3)
'''


@pytest.fixture
def fake_make(tmp_path, monkeypatch):
    script = tmp_path / "fake_make.py"
    script.write_text(FAKE_MAKE, encoding="utf-8")
    monkeypatch.setattr(sim_runner, "MAKE_COMMAND", [sys.executable, str(script)])
    monkeypatch.setattr(sim_runner, "LOCK_PATH", tmp_path / ".sim.lock")
    monkeypatch.setattr(sim_runner, "TESTS_DIR", tmp_path)
    return tmp_path


def _is_gone(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as handle:
            stat = handle.read()
    except FileNotFoundError:
        return True
    # The state letter follows the last ")" in the stat line, because the command name may contain ")".
    state = stat.rsplit(")", 1)[1].split()[0]
    return state == "Z"


def _wait_until_gone(pid):
    deadline = time.monotonic() + 5
    while not _is_gone(pid):
        if time.monotonic() > deadline:
            pytest.fail(f"child process {pid} is still running after the timeout")
        time.sleep(0.1)


def test_success_returns_validated_records(fake_make, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "ok")
    records = sim_runner.run_replays(RUNS, timeout_s=30)
    assert [record["name"] for record in records] == ["A", "B"]
    assert all(set(record) == RECORD_KEYS for record in records)
    assert records[0]["source"] == RUNS[0]["source"]
    assert records[0]["report"] == "[]"
    assert records[0]["replayed_state"] is None
    assert sim_runner.flock_held() is False


def test_nonzero_exit_gives_last_stderr_line(fake_make, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "fail")
    with pytest.raises(sim_runner.SimulationFailed) as exc:
        sim_runner.run_replays(RUNS, timeout_s=30)
    assert exc.value.message == "last line"
    assert sim_runner.flock_held() is False


@pytest.mark.skipif(not os.path.isdir("/proc"), reason="the process check reads /proc, so it needs Linux")
def test_timeout_kills_the_whole_process_group(fake_make, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "hang")
    pid_file = fake_make / "child.pid"
    monkeypatch.setenv("FAKE_PID_FILE", str(pid_file))
    with pytest.raises(sim_runner.SimulationTimeout):
        sim_runner.run_replays(RUNS, timeout_s=1)
    child_pid = int(pid_file.read_text(encoding="utf-8"))
    _wait_until_gone(child_pid)
    assert sim_runner.flock_held() is False


def test_held_lock_gives_busy(fake_make, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "ok")
    fd = os.open(fake_make / ".sim.lock", os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert sim_runner.flock_held() is True
        with pytest.raises(sim_runner.SimulationBusy):
            sim_runner.run_replays(RUNS, timeout_s=30)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    assert sim_runner.flock_held() is False


def test_lock_is_free_again_after_each_case(fake_make, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "ok")
    sim_runner.run_replays(RUNS, timeout_s=30)
    assert sim_runner.flock_held() is False

    monkeypatch.setenv("FAKE_MODE", "fail")
    with pytest.raises(sim_runner.SimulationFailed):
        sim_runner.run_replays(RUNS, timeout_s=30)
    assert sim_runner.flock_held() is False

    monkeypatch.setenv("FAKE_MODE", "ok")
    records = sim_runner.run_replays(RUNS, timeout_s=30)
    assert [record["name"] for record in records] == ["A", "B"]
    assert sim_runner.flock_held() is False


def test_bad_output_is_rejected(fake_make, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "badout")
    with pytest.raises(sim_runner.SimulationFailed) as exc:
        sim_runner.run_replays(RUNS, timeout_s=30)
    assert exc.value.message == "the simulation wrote an unreadable result"
    assert sim_runner.flock_held() is False


def test_missing_output_is_rejected(fake_make, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "noout")
    with pytest.raises(sim_runner.SimulationFailed) as exc:
        sim_runner.run_replays(RUNS, timeout_s=30)
    assert exc.value.message == "the simulation finished without writing a result"
    assert sim_runner.flock_held() is False


def test_invalid_runs_are_rejected_before_any_file_work(fake_make):
    with pytest.raises(ValueError):
        sim_runner.run_replays([], timeout_s=1)
    with pytest.raises(ValueError):
        sim_runner.run_replays([{"name": "A"}], timeout_s=1)
    assert not (fake_make / ".sim.lock").exists()


def test_module_constants():
    assert sim_runner.SIM_MODULE == "snippet_run"
    assert sim_runner.LOCK_PATH.name == ".sim.lock"
    assert sim_runner.LOCK_PATH == sim_runner.REPO_ROOT / "tests" / ".sim.lock"
