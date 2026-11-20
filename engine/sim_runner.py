"""Replay runner for the demo CLI and the Backend.

Pure Python. This module imports no cocotb. run_replays is the only replay entry
point for the CLI and the Backend. It runs make on the snippet_run cocotb module
while holding the tests/.sim.lock file lock, and it returns validated records.
"""

import fcntl
import json
import os
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path

from engine.replayed_state import validate_replayed_state

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKE_COMMAND = ["make"]  # unit tests replace this with a fake command
TESTS_DIR = REPO_ROOT / "tests"
LOCK_PATH = TESTS_DIR / ".sim.lock"
SIM_MODULE = "snippet_run"
STDERR_LIMIT = 300

_RECORD_FIELDS = ("name", "source", "report", "replayed_state")
_RECORD_KEYS = frozenset(_RECORD_FIELDS)
_UNREADABLE = "the simulation wrote an unreadable result"
_NO_RESULT = "the simulation finished without writing a result"


class SimulationBusy(Exception):
    """Another run holds tests/.sim.lock."""


class SimulationTimeout(Exception):
    """The simulation ran longer than timeout_s. Its process group was killed."""


class SimulationFailed(Exception):
    """The simulation exited with an error, or it wrote no valid result."""

    def __init__(self, message):
        self.message = message
        super().__init__(message)


def run_replays(runs, timeout_s):
    """Replay each run through make and return one validated record per run, in order.

    Raises ValueError for invalid runs, SimulationBusy when the lock is held,
    SimulationTimeout when timeout_s passes, and SimulationFailed for other failures.
    """
    _check_runs(runs)
    lock_fd = _take_lock()
    tmp = None
    try:
        tmp = Path(tempfile.mkdtemp())
        return _replay_in(tmp, runs, timeout_s)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)


def flock_held():
    """Return True if another holder has tests/.sim.lock locked."""
    fd = os.open(LOCK_PATH, os.O_CREAT | os.O_RDWR)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


def _check_runs(runs):
    if not isinstance(runs, list) or not runs:
        raise ValueError("runs must be a non-empty list")
    for index, run in enumerate(runs):
        if (
            not isinstance(run, dict)
            or not isinstance(run.get("name"), str)
            or not isinstance(run.get("source"), str)
        ):
            raise ValueError(f"runs[{index}] must be a dict with str name and str source")


def _take_lock():
    fd = os.open(LOCK_PATH, os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise SimulationBusy("another simulation holds tests/.sim.lock") from None
    except BaseException:
        os.close(fd)
        raise
    return fd


def _replay_in(tmp, runs, timeout_s):
    runs_path = tmp / "runs.json"
    out_path = tmp / "out.json"
    stdout_path = tmp / "stdout.txt"
    stderr_path = tmp / "stderr.txt"
    runs_path.write_bytes(json.dumps({"runs": runs}).encode("utf-8"))

    env = dict(os.environ)
    env["REGSPECTRE_RUN_IN"] = str(runs_path)
    env["REGSPECTRE_RUN_OUT"] = str(out_path)
    command = list(MAKE_COMMAND) + [f"COCOTB_TEST_MODULES={SIM_MODULE}"]

    # The child keeps its own copies of these descriptors after Popen returns,
    # so the parent can close them once the wait is over.
    with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
        proc = subprocess.Popen(
            command,
            cwd=TESTS_DIR,
            env=env,
            stdout=stdout_file,
            stderr=stderr_file,
            start_new_session=True,
        )
        _wait_or_kill(proc, timeout_s)

    if proc.returncode != 0:
        raise SimulationFailed(_failure_message(stderr_path, stdout_path, proc.returncode))
    if not out_path.exists():
        raise SimulationFailed(_NO_RESULT)
    return _read_records(out_path, runs)


def _wait_or_kill(proc, timeout_s):
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        _signal_group(proc, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _signal_group(proc, signal.SIGKILL)
            proc.wait()
        raise SimulationTimeout(f"simulation ran longer than {timeout_s} seconds") from None


def _signal_group(proc, sig):
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        pass


def _failure_message(stderr_path, stdout_path, returncode):
    return (
        _summary_line(stderr_path)
        or _summary_line(stdout_path)
        or f"make exited with status {returncode}"
    )


def _summary_line(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [line for line in text.split("\n") if line.strip()]
    if not lines:
        return ""
    return lines[-1].replace("\r", "").strip()[:STDERR_LIMIT]


def _read_records(out_path, runs):
    try:
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("result is not a JSON object")
        records = payload["records"]
        if not isinstance(records, list) or len(records) != len(runs):
            raise ValueError("records do not match runs in count")
        checked = []
        for run, record in zip(runs, records):
            if not isinstance(record, dict) or set(record) != _RECORD_KEYS:
                raise ValueError("record does not have exactly the four keys")
            if record["name"] != run["name"] or record["source"] != run["source"]:
                raise ValueError("record does not match its run")
            if not isinstance(record["report"], str):
                raise ValueError("report is not a string")
            validate_replayed_state(record["replayed_state"])
            checked.append({field: record[field] for field in _RECORD_FIELDS})
    except (OSError, ValueError, KeyError) as exc:
        raise SimulationFailed(_UNREADABLE) from exc
    return checked
