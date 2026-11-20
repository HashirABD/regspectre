"""FastAPI app for the RegSpectre Studio, the local Backend.

The app runs only on the loopback address that the start command chooses.
It imports no LLM client and no network client library. It never writes the
Snapshot, and it runs simulations only through engine.sim_runner.
"""

import threading

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.validation import ErrorReply, validate_run_request
from engine.sim_runner import (
    SimulationBusy,
    SimulationFailed,
    SimulationTimeout,
    flock_held,
    run_replays,
)
from engine.snippets import DEMO_SOURCES

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)

SIM_LOCK = threading.Lock()
RUN_TIMEOUT_S = 60.0
UNEXPECTED_MESSAGE = "the backend hit an unexpected error"
ONE_LINE_LIMIT = 300


def one_line(text):
    """Turn text into one line: no CR or LF, trimmed, at most ONE_LINE_LIMIT characters."""
    return text.replace("\r", " ").replace("\n", " ").strip()[:ONE_LINE_LIMIT]


def busy_response():
    return JSONResponse({"error": "busy"}, status_code=409)


@app.get("/api/status")
async def get_status():
    return {"busy": SIM_LOCK.locked() or flock_held()}


@app.get("/api/snippets")
async def get_snippets():
    return [{"name": name, "source": source} for name, source in DEMO_SOURCES]


@app.post("/api/run")
async def post_run(request: Request):
    raw = await request.body()
    checked = validate_run_request(raw)
    if isinstance(checked, ErrorReply):
        return JSONResponse(checked.body, status_code=checked.status)
    if not SIM_LOCK.acquire(blocking=False):
        return busy_response()
    try:
        records = await run_in_threadpool(run_replays, checked.as_run(), RUN_TIMEOUT_S)
    except SimulationBusy:
        return busy_response()
    except SimulationTimeout:
        return JSONResponse({"error": "timeout"}, status_code=504)
    except SimulationFailed as exc:
        return JSONResponse(
            {"error": "simulation_failed", "message": one_line(exc.message)},
            status_code=500,
        )
    except Exception:
        return JSONResponse(
            {"error": "simulation_failed", "message": UNEXPECTED_MESSAGE},
            status_code=500,
        )
    else:
        record = records[0]
        return JSONResponse(
            {"report": record["report"], "replayed_state": record["replayed_state"]},
            status_code=200,
        )
    finally:
        SIM_LOCK.release()
