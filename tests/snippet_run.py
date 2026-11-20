"""Shared replay module for the demo CLI and the Backend.

This is the one shared replay path. The demo CLI and the Backend both replay
their C snippets on the real RTL through this cocotb module.

It runs quiet replays only (seed None). Its only file output is the path in
REGSPECTRE_RUN_OUT. It never opens the recorded Snapshot and writes no other
file.

Input comes from the path in REGSPECTRE_RUN_IN, a JSON file shaped as
{"runs": [{"name": str, "source": str}, ...]}.
"""

import json
import os

import cocotb

from engine.bus_driver import BusDriver
from engine.c_parser import parse
from engine.demo import run_c_rdr_source, run_c_source


def _input_runs():
    """Return the validated run list from the file named by REGSPECTRE_RUN_IN."""
    path = os.environ.get("REGSPECTRE_RUN_IN")
    if not path:
        raise RuntimeError("REGSPECTRE_RUN_IN is not set")
    if not os.path.isfile(path):
        raise RuntimeError(f"REGSPECTRE_RUN_IN file not found: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    runs = data.get("runs") if isinstance(data, dict) else None
    if not isinstance(runs, list):
        raise ValueError("input must be an object with a 'runs' list")
    for index, run in enumerate(runs):
        if not isinstance(run, dict):
            raise ValueError(f"run {index} must be an object")
        if not isinstance(run.get("name"), str):
            raise ValueError(f"run {index} 'name' must be a string")
        if not isinstance(run.get("source"), str):
            raise ValueError(f"run {index} 'source' must be a string")
    return runs


def _output_path():
    """Return the path from REGSPECTRE_RUN_OUT, which must be set."""
    path = os.environ.get("REGSPECTRE_RUN_OUT")
    if not path:
        raise RuntimeError("REGSPECTRE_RUN_OUT is not set")
    return path


@cocotb.test()
async def replay_runs(dut):
    """Replay each run on the RTL and write the records to REGSPECTRE_RUN_OUT."""
    runs = _input_runs()
    out_path = _output_path()
    bus = BusDriver(dut)
    await bus.start()
    records = []
    for run in runs:
        source = run["source"]
        ops = parse(source)
        trace = {}
        if any(op.reg == "UART_RDR" for op in ops):
            reports, text = await run_c_rdr_source(dut, source, seed=None, trace=trace)
        else:
            reports, text = await run_c_source(dut, source, seed=None, trace=trace)
        records.append({
            "name": run["name"],
            "source": source,
            "report": text,
            "replayed_state": trace["replayed_state"],
        })
    with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps({"records": records}, indent=2) + "\n")
