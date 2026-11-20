"""Backend API tests for the Studio Backend (design section 7.2).

The tests use FastAPI's TestClient. Every test that reaches POST /api/run
replaces backend.app.run_replays with a fake, so no simulator runs. This file
does not import cocotb.
"""

import fcntl
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend.app
import engine.sim_runner
import engine.snapshot
from backend.validation import USER_SNIPPET, count_lines
from engine.sim_runner import SimulationBusy, SimulationFailed, SimulationTimeout
from engine.snippets import DEMO_SNIPPET_NAMES, DEMO_SOURCES

FAKE_REPORT = '[\n  {"register": "UART_ISR", "bit": 3}\n]\n'
FAKE_STATE = {"register": "UART_ISR", "pre": 9, "post": 0}
DEMO_SOURCE_BY_NAME = dict(DEMO_SOURCES)
USER_C_SOURCE = "void h(void) {\n UART_ISR = (1U << TX_DONE);\n}\n"
LOOP_C_SOURCE = "void h(void) {\n for (;;) {}\n}\n"
U2028_SOURCE = "void h(void) {\u2028 UART_ISR = (1U << TX_DONE);\u2028}"
INVALID_BODIES = [
    b"{not json",
    b"[]",
    b'{"snippet": "ISR_RMW_SNIPPET", "x": 1}',
    b'{"snippet": "ISR_RMW_SNIPPET", "c_source": "void h(void) {}"}',
    b"{}",
    b'{"snippet": "NOT_A_NAME"}',
    b'{"snippet": 5}',
]
ORDER_CASES = ["oversized", "bad_name", "parser_error", "valid"]
CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]


def _lines_snippet(n_statements):
    """Return a handler with n_statements assignment lines. Its line count is n_statements + 2."""
    return "void h(void) {\n" + " UART_ISR = (1U << TX_DONE);\n" * n_statements + "}\n"


def _default_records(runs):
    return [
        {
            "name": run["name"],
            "source": run["source"],
            "report": FAKE_REPORT,
            "replayed_state": FAKE_STATE,
        }
        for run in runs
    ]


def _raising(exc):
    def behaviour(runs, timeout_s):
        raise exc

    return behaviour


def _post_json(client, body):
    return client.post("/api/run", json=body)


def _post_raw(client, raw):
    return client.post("/api/run", content=raw, headers={"Content-Type": "application/json"})


def _cors_preflight(client, origin):
    return client.options(
        "/api/run",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


def _order_body(case):
    if case == "oversized":
        return {"c_source": _lines_snippet(199)}
    if case == "bad_name":
        return {"snippet": "NOT_A_NAME"}
    if case == "parser_error":
        return {"c_source": LOOP_C_SOURCE}
    return {"c_source": USER_C_SOURCE}


def _expected_order_reply(case, busy):
    if case == "oversized":
        return 400, {"error": "too_large"}
    if case == "bad_name":
        return 400, {"error": "invalid_request"}
    if case == "parser_error":
        return 422, None
    if busy:
        return 409, {"error": "busy"}
    return 200, None


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(engine.sim_runner, "LOCK_PATH", tmp_path / ".sim.lock")
    monkeypatch.setattr(
        engine.snapshot,
        "SNAPSHOT_PATH",
        tmp_path / "snap" / "snap.json",
    )
    yield
    assert backend.app.SIM_LOCK.locked() is False, "the test left SIM_LOCK held"


@pytest.fixture
def client():
    return TestClient(backend.app.app)


@pytest.fixture
def fake(monkeypatch):
    """Return an installer. Call it as fake() or fake(behaviour=...); it returns the calls list."""

    def install(behaviour=None):
        calls = []

        def fake_run_replays(runs, timeout_s):
            calls.append((runs, timeout_s))
            if behaviour is not None:
                return behaviour(runs, timeout_s)
            return _default_records(runs)

        monkeypatch.setattr(backend.app, "run_replays", fake_run_replays)
        return calls

    return install


def test_status_is_false_at_start(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json() == {"busy": False}


def test_status_is_true_while_sim_lock_is_held(client):
    backend.app.SIM_LOCK.acquire()
    try:
        response = client.get("/api/status")
        assert response.json() == {"busy": True}
    finally:
        backend.app.SIM_LOCK.release()

    fd = os.open(engine.sim_runner.LOCK_PATH, os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            response = client.get("/api/status")
            assert response.json() == {"busy": True}
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def test_snippets_return_four_entries_in_order(client):
    response = client.get("/api/snippets")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 4
    for item in body:
        assert isinstance(item, dict)
        assert set(item) == {"name", "source"}
    assert [item["name"] for item in body] == list(DEMO_SNIPPET_NAMES)
    for item in body:
        assert item["source"] == DEMO_SOURCE_BY_NAME[item["name"]]


def test_demo_snippet_success_returns_exactly_report_and_state(client, fake):
    calls = fake()
    response = _post_json(client, {"snippet": "ISR_RMW_SNIPPET"})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"report", "replayed_state"}
    assert body["report"] == FAKE_REPORT
    assert body["replayed_state"] == FAKE_STATE
    assert len(calls) == 1
    runs, timeout_s = calls[0]
    assert runs == [{"name": "ISR_RMW_SNIPPET", "source": DEMO_SOURCE_BY_NAME["ISR_RMW_SNIPPET"]}]
    assert timeout_s == backend.app.RUN_TIMEOUT_S


def test_user_snippet_success_uses_user_name(client, fake):
    calls = fake()
    response = _post_json(client, {"c_source": USER_C_SOURCE})
    assert response.status_code == 200
    assert len(calls) == 1
    runs, _ = calls[0]
    assert runs == [{"name": USER_SNIPPET, "source": USER_C_SOURCE}]


def test_timeout_gives_504_without_report(client, fake):
    fake(behaviour=_raising(SimulationTimeout("x")))
    response = _post_json(client, {"snippet": "ISR_RMW_SNIPPET"})
    assert response.status_code == 504
    body = response.json()
    assert body == {"error": "timeout"}
    assert "report" not in body


def test_failed_replay_gives_500_with_one_line_message(client, fake):
    fake(behaviour=_raising(SimulationFailed("line one\nline two")))
    response = _post_json(client, {"snippet": "ISR_RMW_SNIPPET"})
    assert response.status_code == 500
    assert response.json() == {"error": "simulation_failed", "message": "line one line two"}


def test_runner_busy_gives_409(client, fake):
    fake(behaviour=_raising(SimulationBusy("x")))
    response = _post_json(client, {"snippet": "ISR_RMW_SNIPPET"})
    assert response.status_code == 409
    assert response.json() == {"error": "busy"}


def test_unexpected_error_gives_500_and_releases_lock(client, fake):
    attempts = []

    def raise_then_succeed(runs, timeout_s):
        attempts.append(runs)
        if len(attempts) == 1:
            raise RuntimeError("boom")
        return _default_records(runs)

    calls = fake(behaviour=raise_then_succeed)
    first = _post_json(client, {"snippet": "ISR_RMW_SNIPPET"})
    assert first.status_code == 500
    assert first.json() == {"error": "simulation_failed", "message": backend.app.UNEXPECTED_MESSAGE}
    assert backend.app.SIM_LOCK.locked() is False

    second = _post_json(client, {"snippet": "ISR_RMW_SNIPPET"})
    assert second.status_code == 200
    assert len(calls) == 2


@pytest.mark.parametrize("raw", INVALID_BODIES)
def test_invalid_bodies_give_400_invalid_request(client, fake, raw):
    calls = fake()
    response = _post_raw(client, raw)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid_request"}
    assert calls == []


def test_bad_utf8_gives_400_invalid_request(client, fake):
    calls = fake()
    response = _post_raw(client, b"\xff\xfe")
    assert response.status_code == 400
    assert response.json() == {"error": "invalid_request"}
    assert calls == []


@pytest.mark.parametrize("busy", [False, True])
@pytest.mark.parametrize("case", ORDER_CASES)
def test_order_matrix(client, fake, busy, case):
    calls = fake()
    body = _order_body(case)
    if busy:
        backend.app.SIM_LOCK.acquire()
    try:
        response = _post_json(client, body)
        assert backend.app.SIM_LOCK.locked() is busy
    finally:
        if busy:
            backend.app.SIM_LOCK.release()

    status, reply = _expected_order_reply(case, busy)
    assert response.status_code == status
    reply_body = response.json()
    if case == "parser_error":
        assert reply_body["error"] == "parser_error"
        assert reply_body["line"] == 2
        assert "message" in reply_body
    elif status == 200:
        assert set(reply_body) == {"report", "replayed_state"}
    else:
        assert reply_body == reply
    assert len(calls) == (1 if status == 200 else 0)


@pytest.mark.parametrize("origin", CORS_ORIGINS)
def test_cors_preflight_allows_local_studio_origins(client, origin):
    response = _cors_preflight(client, origin)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_rejects_other_origin(client):
    response = _cors_preflight(client, "http://evil.example:3000")
    assert "access-control-allow-origin" not in response.headers


def test_snapshot_is_not_created_or_changed_by_a_run(client, fake):
    fake()
    snapshot_path = engine.snapshot.SNAPSHOT_PATH
    assert not snapshot_path.exists()
    response = _post_json(client, {"snippet": "ISR_RMW_SNIPPET"})
    assert response.status_code == 200
    assert not snapshot_path.exists()

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_bytes(b"old\n")
    response = _post_json(client, {"snippet": "ISR_RMW_SNIPPET"})
    assert response.status_code == 200
    assert snapshot_path.read_bytes() == b"old\n"


def test_no_0_0_0_0_text_in_backend():
    backend_dir = Path(__file__).resolve().parents[1] / "backend"
    files = sorted(backend_dir.rglob("*.py"))
    assert files, "no Python files found under backend/"
    offenders = [str(path) for path in files if "0.0.0.0" in path.read_text(encoding="utf-8")]
    assert offenders == []


def test_200_lines_is_accepted(client, fake):
    text = _lines_snippet(198)
    assert count_lines(text) == 200
    calls = fake()
    response = _post_json(client, {"c_source": text})
    assert response.status_code == 200
    assert len(calls) == 1


def test_201_lines_is_too_large(client, fake):
    text = _lines_snippet(199)
    assert count_lines(text) == 201
    calls = fake()
    response = _post_json(client, {"c_source": text})
    assert response.status_code == 400
    assert response.json() == {"error": "too_large"}
    assert calls == []


def test_u2028_counts_as_one_line_and_is_accepted(client, fake):
    assert count_lines(U2028_SOURCE) == 1
    calls = fake()
    response = _post_raw(client, json.dumps({"c_source": U2028_SOURCE}).encode("utf-8"))
    assert response.status_code == 200
    assert len(calls) == 1
