"""cocotb module that replays the four demo snippets and writes the records to a JSON file.

Only engine.demo run uses this module. That command sets REGSPECTRE_DEMO_OUT to the
output path and runs make with COCOTB_TEST_MODULES=demo_print. The module is not in
the default list in tests/Makefile. Its name does not start with test_, so pytest does
not collect it.

Each record has name, source (the C snippet text) and report (the JSON text returned
by run_c_source or run_c_rdr_source with seed None).
"""

import json
import os

import cocotb

from engine.bus_driver import BusDriver
from engine.demo import (
    ISR_DIRECT_SNIPPET,
    ISR_RMW_SNIPPET,
    RDR_DOUBLE_READ_SNIPPET,
    RDR_SINGLE_READ_SNIPPET,
    run_c_rdr_source,
    run_c_source,
)

OUTPUT_ENV = "REGSPECTRE_DEMO_OUT"


@cocotb.test()
async def write_demo_reports(dut):
    """Replay each snippet with seed None and write the records to the output file."""
    out_path = os.environ.get(OUTPUT_ENV)
    if not out_path:
        raise RuntimeError(f"{OUTPUT_ENV} must name the JSON output file")

    bus = BusDriver(dut)
    await bus.start()

    runs = (
        ("ISR_RMW_SNIPPET", ISR_RMW_SNIPPET, run_c_source),
        ("ISR_DIRECT_SNIPPET", ISR_DIRECT_SNIPPET, run_c_source),
        ("RDR_DOUBLE_READ_SNIPPET", RDR_DOUBLE_READ_SNIPPET, run_c_rdr_source),
        ("RDR_SINGLE_READ_SNIPPET", RDR_SINGLE_READ_SNIPPET, run_c_rdr_source),
    )
    records = []
    for name, source, runner in runs:
        _, report_text = await runner(dut, source, seed=None)
        records.append({"name": name, "source": source, "report": report_text})

    with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(records, handle, indent=2)
