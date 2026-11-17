# Implementation Plan: uart_core

## Overview

Build the first RegSpectre co-verification core for a UART peripheral in the order the user specified: the SystemVerilog RTL first, then the deterministic Python engine component-by-component (register map → bus driver → C parser → intended-state model → violation detector → report writer), then an end-to-end demo that prints JSON violation reports for the two target bugs, and finally the Hypothesis property tests including the Requirement 9 RTL-integration test.

Every task ends with a runnable verification step (a cocotb run, a pytest run, or the demo) that must pass before moving on, so each task is independently committable. All tasks are required (none optional). The Next.js `web/` studio, DMA, watchdog, and any MCP server are out of scope.

Implementation detail lives in `design.md` and `requirements.md` — these tasks name the files, the behavior, the requirements covered, and the verification step, without re-deriving the design. Run all commands with the Python venv active (`~/.venv`); cocotb tests run via `cd tests && make`, Python tests via `pytest`.

## Tasks

- [ ] 1. UART_Core RTL and cocotb tests
  - Create `rtl/uart_ctrl.sv` implementing the `uart_ctrl` module exactly per the design's RTL section: 4-bit `isr`, 8-bit `rdr`, address decode (`ISR_ADDR=0x40001004`, `RDR_ADDR=0x40001008`), combinational zero-extended read, W1C `clear_mask` on writable bits 0/2/3 (`4'b1101`), `rdr_clear_mask` clearing RX_READY (bit 1) on an RDR read, `hwset_mask` with `overrun = rx_valid & isr[1] & ~rdr_read` and `hw_set` priority ORed last, `isr_next = (isr & ~clear_mask & ~rdr_clear_mask) | hwset_mask`, `rdr_next = rx_valid ? rx_data : (rdr_read ? 0 : rdr)`, and an async reset that zeroes both registers.
  - Create `tests/test_uart_ctrl.py` with one cocotb test per acceptance criterion of Requirements 1 and 2: W1C clear on write-1, write-0 no-op, `hw_set` sets a bit, reset zeroes both, `rx_valid` loads `rdr` and sets RX_READY, same-cycle `hw_set`/W1C priority leaves the bit set, writes to RX_READY are ignored, RDR read returns the old value then clears RDR and RX_READY, and an address-decode miss returns `rdata=0` with no register change.
  - Extend `tests/Makefile` with a `uart_ctrl` target (`VERILOG_SOURCES` adds `../rtl/uart_ctrl.sv`, `COCOTB_TOPLEVEL=uart_ctrl`, `COCOTB_TEST_MODULES` includes `test_uart_ctrl`) without breaking the existing `w1c_smoke` build.
  - Covers: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 2.1
  - Verify: `cd tests && make` compiles `uart_ctrl.sv` and runs `test_uart_ctrl.py` with all assertions passing. Commit.

- [ ] 2. Register map and bit-type symbol table
  - Create `engine/regmap.py` with the `REGISTERS` table from the design: `UART_ISR` (addr `0x40001004`, width 4, bits 0 TX_DONE W1C, 1 RX_READY RO, 2 PARITY_ERR W1C, 3 OVERRUN_ERR W1C) and `UART_RDR` (addr `0x40001008`, width 8, bits 0-7 RTC), plus `ISR_ADDR`/`RDR_ADDR` constants and helper lookups (address→name, bit-name→index, and a bit-type query). This table is the single source of register/bit metadata for the parser, intended model, detector, and report writer.
  - Add regmap unit tests to `tests/test_engine_unit.py` asserting the addresses, bit names/types, and lookup helpers.
  - Covers: Requirements 1.1, 3.4, 7.1
  - Verify: `pytest tests/test_engine_unit.py -k regmap` passes. Commit.

- [ ] 3. cocotb bus driver with cycle stamping and seeded determinism
  - Create `engine/bus_driver.py` as a thin async cocotb wrapper over the DUT per the design: `write(addr, data)` drives `we=1, re=0` and returns the commit `cycle`; `read(addr)` drives `we=0, re=1` and returns `(rdata, cycle)`; `rmw(addr, mask, mode)` does a read then a write of the computed value (`SET` → `old | mask`, `CLR` → `old & ~mask`) and returns `(old, new, cycle)`. Each transaction commits on one rising edge and signals are deasserted between transactions; `cycle` counts `posedge clk` since the last reset. Drive the `hw_set` schedule between/around transactions from `random.Random(seed)` so identical `(rtl, c_snippet, seed)` produces identical sim input.
  - Create `tests/test_bus_driver.py` (cocotb) that uses the driver against `uart_ctrl` to write/read/rmw and asserts correct `rdata` values, monotonic `cycle` stamps, and that two runs with the same seed drive identical `hw_set`.
  - Add `test_bus_driver` to the `uart_ctrl` Makefile target's `COCOTB_TEST_MODULES`.
  - Covers: Requirements 3.1, 3.2, 3.3, 8.1
  - Verify: `cd tests && make` runs `test_bus_driver.py` and all assertions pass. Commit.

- [ ] 4. C-subset parser to operations
  - Create `engine/c_parser.py` that parses the fixed C subset (not a compiler) per the design: direct assignment, compound `|=`, compound `&=`, a register read into a local, a `UART_RDR` read, and handler scope markers. Each statement becomes an `Operation` (define the `Operation` dataclass here) carrying `kind`, `reg`, `mask`, `mode`, and the 1-based `c_line`. Use `regmap` as the symbol table; restrict expressions to `(1U << BIT)`, integer constants, `~`, `|`, `&`, and bit-name references. Reject loops, function calls, pointer arithmetic, and conditionals with a `ParseError` naming the offending line.
  - Add parser unit tests to `tests/test_engine_unit.py` asserting each construct maps to the correct `Operation` (and `c_line`), and that unsupported constructs raise `ParseError` with the right line.
  - Covers: Requirements 3.3, 3.4, 3.5
  - Verify: `pytest tests/test_engine_unit.py -k parser` passes. Commit.

- [ ] 5. Intended-state model
  - Create `engine/intended_model.py` with the pure function `intended_state(op, pre) -> Intended_State` per the design: bits outside the named mask `M` equal `pre[i]`; bits inside `M` follow W1C write semantics (`0` if the written value has bit `i` set, else `pre[i]`). Handle direct assignment (`M={BIT}`, clears only `BIT`), RMW `SET` (`written = pre | M`), and RMW `CLR` (`written = pre & ~M`, a write-0 no-op on `M`). It reads bit types from `regmap` and the `Operation` from the parser.
  - Add intended-model unit tests to `tests/test_engine_unit.py` checking all three operation kinds across representative and edge `pre` states.
  - Covers: Requirements 4.1, 4.4, 3.3
  - Verify: `pytest tests/test_engine_unit.py -k intended` passes. Commit.

- [ ] 6. Violation detector (neighbor corruption and double read)
  - Create `engine/detector.py` with a pure comparison of `Intended_State` vs `Actual_State` (read from the RTL by the bus driver). Define the `Violation_Report` dataclass here (`register`, `bit`, `intended`, `actual`, `cycle`, `c_line`). Emit a report only for the loss pattern Intended=1, Actual=0. For an RMW on `UART_ISR`, emit one report per pending W1C bit outside `M` that was cleared (bit, intended=1, actual=0, the RMW commit `cycle`, `c_line` if from a snippet); a direct assignment clears only its target so emits nothing. Scope `READ` operations to their enclosing handler: the first `UART_RDR` read is the baseline (no report); a second `UART_RDR` read in the same handler emits one report per bit that was 1 in the first read and 0 in the second (`register=UART_RDR`, intended=1, actual=0, the second read's `cycle`, `c_line` if from a snippet); a single RDR read emits nothing.
  - Add detector unit tests to `tests/test_engine_unit.py` covering neighbor-corruption flagging, direct-assignment cleanliness, double-read flagging, and single-read cleanliness.
  - Covers: Requirements 4.2, 4.3, 5.1, 5.2, 5.3, 6.1, 6.2
  - Verify: `pytest tests/test_engine_unit.py -k detector` passes. Commit.

- [ ] 7. Report writer (JSON serialization)
  - Create `engine/report.py` that serializes `Violation_Report` records (imported from `engine/detector.py`) to JSON with typed fields: `register` (string), `bit` (non-negative int), `intended` (0|1), `actual` (0|1), `cycle` (non-negative int), and `c_line` (int). Include `c_line` when the operation came from a parsed C snippet and omit it for a raw transaction list. Validate the field types before serializing.
  - Add report unit tests to `tests/test_engine_unit.py` asserting JSON validity, the `c_line` presence rules, and that parsing serialized JSON yields an equivalent report.
  - Covers: Requirements 7.1, 7.2, 7.3
  - Verify: `pytest tests/test_engine_unit.py -k report` passes. Commit.

- [ ] 8. End-to-end demo and determinism
  - Create `engine/demo.py` that wires the full pipeline (parser → bus driver → `uart_ctrl` sim → intended model → detector → report writer) and runs two C snippets: one ISR read-modify-write that clears a pending neighbor interrupt bit, and one handler that reads `UART_RDR` twice. Print the JSON violation reports for each. Make the script self-verifying: assert the first snippet yields the expected neighbor-corruption report(s) and the second yields the expected double-read reports, and assert that a second seeded run produces byte-identical JSON. The demo uses only deterministic Python (no LLM/network).
  - The end-to-end determinism checks are cocotb tests: `test_seed_determinism` in `tests/test_bus_driver.py`, and `test_demo_isr_rmw_three_quiet_runs_are_byte_identical` in `tests/test_demo.py`. The no-LLM structural check (assert `engine/` imports no LLM client and makes no network calls) is in `tests/test_no_llm.py` (pytest, six tests), not in `tests/test_engine_unit.py`.
  - Covers: Requirements 3.2, 5.1, 6.1, 8.1, 8.2
  - Verify: `cd tests && make` runs the demo checks in `tests/test_demo.py`, which replay the snippets on the RTL and check the JSON reports. `python -m engine.demo` exits 0 and prints only a usage message. It does not run cocotb and prints no reports. `pytest tests/test_no_llm.py` passes (6 tests). Commit.

- [ ] 9. Hypothesis property tests including the Requirement 9 RTL integration
  - Create `tests/test_engine_props.py` with Hypothesis property tests (`@settings(derandomize=True, max_examples=100, deadline=None)`), one per design Property 1-7, each tagged with its property number: Property 1 parser round-trip (Req 3.4); Property 2 intended-state respects the named mask (Req 4.1, 4.4, 3.3); Property 3 RMW flags exactly the lost bits (Req 4.3, 5.1); Property 4 direct assignment produces no violations (Req 5.2); Property 5 `c_line` presence matches the source (Req 5.3, 7.2, 7.3); Property 6 double-read detection (Req 6.1, 6.2); Property 7 report JSON validity and round-trip (Req 7.1).
  - Create `tests/test_pbt_hw_timing.py` (cocotb) implementing Property 8 (Requirement 9): Hypothesis generates a random per-cycle `hw_set` schedule, a target bit `BIT`, and a write cycle; compile `uart_ctrl.sv` once, then per example reset the DUT, apply the schedule, issue `UART_ISR = (1U << BIT)` via the bus driver, and assert no W1C bit other than `BIT` transitions set→cleared (else fail with a neighbor-wipeout indication). Use at least 100 examples, and state in the docstring/output that this is randomized testing, not proof of correctness.
  - Add `test_pbt_hw_timing` to the `uart_ctrl` Makefile target's `COCOTB_TEST_MODULES`.
  - Covers: Requirements 3.4, 4.1, 4.3, 4.4, 5.1, 5.2, 5.3, 6.1, 6.2, 7.1, 7.2, 7.3, 9.1, 9.2, 9.3, 9.4
  - Verify: `pytest tests/test_engine_props.py` passes. The run uses a fixed derandomized seed (`derandomize=True`). Properties 1, 2, 3, 6 and 7 ran 100 examples each. Property 4 ran 64 and Property 5 ran 32, because their input space was exhausted. This is randomized testing, not a proof. `cd tests && make` runs `test_pbt_hw_timing.py` with >=100 examples and no neighbor wipeout. Commit.

- [ ] 10. Final checkpoint - run the full suite
  - Run the complete test suite. `cd tests && make` runs 33 cocotb tests from the modules `test_uart_ctrl`, `test_bus_driver`, `test_demo`, `test_pbt_hw_timing`, `test_pbt_negative_control` and `test_pbt_pipeline_negative_control`. `pytest tests/` runs 100 tests (87 engine unit, 6 no LLM, 7 properties) and does not collect the cocotb files. Both must pass. Ensure everything passes together as an integrated whole.
  - Covers: integration validation across Requirements 1-9
  - Verify: `cd tests && make` and `pytest tests/` both pass with no failures. Ask the user if questions arise.

## Notes

- All tasks are required; none are optional or star-marked.
- Tasks are ordered for sequential execution: each ends with a passing verification step so a commit is possible before starting the next. The dependency graph encodes this order; several tasks share `tests/test_engine_unit.py` and `tests/Makefile`, which is why they run in separate waves.
- `Operation` is defined in `engine/c_parser.py` (task 4); `Violation_Report` is defined in `engine/detector.py` (task 6) and imported by `engine/report.py` (task 7) to avoid circular imports.
- Implementation detail is in `design.md`; requirement text is in `requirements.md`. Out of scope: `web/` studio, DMA, watchdog, MCP.
- Property tests (task 9) implement the eight design Correctness Properties and are described as randomized testing, not proof of correctness (Requirement 9.4).

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2"] },
    { "id": 2, "tasks": ["3"] },
    { "id": 3, "tasks": ["4"] },
    { "id": 4, "tasks": ["5"] },
    { "id": 5, "tasks": ["6"] },
    { "id": 6, "tasks": ["7"] },
    { "id": 7, "tasks": ["8"] },
    { "id": 8, "tasks": ["9"] },
    { "id": 9, "tasks": ["10"] }
  ]
}
```
