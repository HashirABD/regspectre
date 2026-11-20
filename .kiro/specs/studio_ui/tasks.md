# Implementation Plan: studio_ui

## Overview

This plan implements `design.md` for the local studio_ui feature (D8: local 127.0.0.1 only, no Docker or public cloud deployment). Every task lists its target files, the Requirement and Design sections it covers, and its verification commands.

## Conventions

- Repository root in WSL: `/home/hashir/regspectre`. Python environment: `/home/hashir/.venv` (Python 3.14, cocotb 2.1.0, Hypothesis, pytest). Activate it with `source /home/hashir/.venv/bin/activate`.
- Simulator: Icarus Verilog 12.0, run through `make` in `tests/`.
- Every verification command runs from the repository root, unless it starts with `cd`.
- Long-running processes (the Backend server and the Next.js development server) are started by the user in a separate terminal. The implementation agent does not start them.
- Decisions D1 to D8 are in the Decisions table of `design.md`. Each task names the decisions it depends on.
- Requirement numbers refer to `requirements.md`. Section numbers refer to `design.md`.
- A task is done only when its verification commands produce the stated result.

## Task Dependency Graph

Phase 1 (strict parser) has no dependencies on the other phases. Phase 2 (replay) needs Phase 1 only for the shared parse helpers. Phase 3 (Snapshot, runner, CLI) needs Phase 2. Phase 4 (Backend) needs Phases 1 and 3. Phase 5 (Studio) needs Phase 4 for the end-to-end check, but its pure modules need only the Studio tooling.
The wave definitions below give the same order as the paragraph above. Tasks in the same wave can run in any order.

```json
{
    "waves":  [
                  {
                      "id":  1,
                      "tasks":  [
                                    "1.1"
                                ],
                      "depends_on":  [

                                     ]
                  },
                  {
                      "id":  2,
                      "tasks":  [
                                    "1.2"
                                ],
                      "depends_on":  [
                                         "1.1"
                                     ]
                  },
                  {
                      "id":  3,
                      "tasks":  [
                                    "1.3"
                                ],
                      "depends_on":  [
                                         "1.2"
                                     ]
                  },
                  {
                      "id":  4,
                      "tasks":  [
                                    "1.4"
                                ],
                      "depends_on":  [
                                         "1.3"
                                     ]
                  },
                  {
                      "id":  5,
                      "tasks":  [
                                    "1.5"
                                ],
                      "depends_on":  [
                                         "1.4"
                                     ]
                  },
                  {
                      "id":  6,
                      "tasks":  [
                                    "1.6"
                                ],
                      "depends_on":  [
                                         "1.5"
                                     ]
                  },
                  {
                      "id":  7,
                      "tasks":  [
                                    "2.1"
                                ],
                      "depends_on":  [
                                         "1.6"
                                     ]
                  },
                  {
                      "id":  8,
                      "tasks":  [
                                    "2.2"
                                ],
                      "depends_on":  [
                                         "2.1"
                                     ]
                  },
                  {
                      "id":  9,
                      "tasks":  [
                                    "2.3"
                                ],
                      "depends_on":  [
                                         "2.2"
                                     ]
                  },
                  {
                      "id":  10,
                      "tasks":  [
                                    "2.4"
                                ],
                      "depends_on":  [
                                         "2.3"
                                     ]
                  },
                  {
                      "id":  11,
                      "tasks":  [
                                    "2.5"
                                ],
                      "depends_on":  [
                                         "2.4"
                                     ]
                  },
                  {
                      "id":  12,
                      "tasks":  [
                                    "2.6"
                                ],
                      "depends_on":  [
                                         "2.5"
                                     ]
                  },
                  {
                      "id":  13,
                      "tasks":  [
                                    "2.7"
                                ],
                      "depends_on":  [
                                         "2.6"
                                     ]
                  },
                  {
                      "id":  14,
                      "tasks":  [
                                    "2.8"
                                ],
                      "depends_on":  [
                                         "2.7"
                                     ]
                  },
                  {
                      "id":  15,
                      "tasks":  [
                                    "2.9"
                                ],
                      "depends_on":  [
                                         "2.8"
                                     ]
                  },
                  {
                      "id":  16,
                      "tasks":  [
                                    "2.10"
                                ],
                      "depends_on":  [
                                         "2.9"
                                     ]
                  },
                  {
                      "id":  17,
                      "tasks":  [
                                    "3.1"
                                ],
                      "depends_on":  [
                                         "2.10"
                                     ]
                  },
                  {
                      "id":  18,
                      "tasks":  [
                                    "3.2"
                                ],
                      "depends_on":  [
                                         "3.1"
                                     ]
                  },
                  {
                      "id":  19,
                      "tasks":  [
                                    "3.3"
                                ],
                      "depends_on":  [
                                         "3.2"
                                     ]
                  },
                  {
                      "id":  20,
                      "tasks":  [
                                    "3.4"
                                ],
                      "depends_on":  [
                                         "3.3"
                                     ]
                  },
                  {
                      "id":  21,
                      "tasks":  [
                                    "3.5"
                                ],
                      "depends_on":  [
                                         "3.4"
                                     ]
                  },
                  {
                      "id":  22,
                      "tasks":  [
                                    "4.1"
                                ],
                      "depends_on":  [
                                         "3.5"
                                     ]
                  },
                  {
                      "id":  23,
                      "tasks":  [
                                    "4.2"
                                ],
                      "depends_on":  [
                                         "4.1"
                                     ]
                  },
                  {
                      "id":  24,
                      "tasks":  [
                                    "4.3"
                                ],
                      "depends_on":  [
                                         "4.2"
                                     ]
                  },
                  {
                      "id":  25,
                      "tasks":  [
                                    "4.4"
                                ],
                      "depends_on":  [
                                         "4.3"
                                     ]
                  },
                  {
                      "id":  26,
                      "tasks":  [
                                    "4.5"
                                ],
                      "depends_on":  [
                                         "4.4"
                                     ]
                  },
                  {
                      "id":  27,
                      "tasks":  [
                                    "4.6"
                                ],
                      "depends_on":  [
                                         "4.5"
                                     ]
                  },
                  {
                      "id":  28,
                      "tasks":  [
                                    "4.7"
                                ],
                      "depends_on":  [
                                         "4.6"
                                     ]
                  },
                  {
                      "id":  29,
                      "tasks":  [
                                    "5.1"
                                ],
                      "depends_on":  [
                                         "4.7"
                                     ]
                  },
                  {
                      "id":  30,
                      "tasks":  [
                                    "5.2"
                                ],
                      "depends_on":  [
                                         "5.1"
                                     ]
                  },
                  {
                      "id":  31,
                      "tasks":  [
                                    "5.3"
                                ],
                      "depends_on":  [
                                         "5.2"
                                     ]
                  },
                  {
                      "id":  32,
                      "tasks":  [
                                    "5.4"
                                ],
                      "depends_on":  [
                                         "5.3"
                                     ]
                  },
                  {
                      "id":  33,
                      "tasks":  [
                                    "5.5"
                                ],
                      "depends_on":  [
                                         "5.4"
                                     ]
                  },
                  {
                      "id":  34,
                      "tasks":  [
                                    "5.6"
                                ],
                      "depends_on":  [
                                         "5.5"
                                     ]
                  },
                  {
                      "id":  35,
                      "tasks":  [
                                    "5.7"
                                ],
                      "depends_on":  [
                                         "5.6"
                                     ]
                  },
                  {
                      "id":  36,
                      "tasks":  [
                                    "5.8"
                                ],
                      "depends_on":  [
                                         "5.7"
                                     ]
                  },
                  {
                      "id":  37,
                      "tasks":  [
                                    "5.9"
                                ],
                      "depends_on":  [
                                         "5.8"
                                     ]
                  },
                  {
                      "id":  38,
                      "tasks":  [
                                    "5.10"
                                ],
                      "depends_on":  [
                                         "5.9"
                                     ]
                  },
                  {
                      "id":  39,
                      "tasks":  [
                                    "5.11"
                                ],
                      "depends_on":  [
                                         "5.10"
                                     ]
                  },
                  {
                      "id":  40,
                      "tasks":  [
                                    "5.12"
                                ],
                      "depends_on":  [
                                         "5.11"
                                     ]
                  }
              ]
}
```

## Tasks

The checkbox tasks are grouped into five phases. Each phase depends on the phases before it, as shown in the dependency graph.

## Phase 1: Engine strict parser (`engine/c_parser.py`)

- [x] 1. Phase 1: add the strict parser entry point to `engine/c_parser.py`

  The existing `parse()` and `_tokenize()` functions stay exactly as they are, including the `splitlines()` call on line 84. All new code is additive. Decisions D4 and D7 apply. Design sections 1.1 to 1.8. Requirement 3, criteria 1 to 20.

  - [x] 1.1 Add message constants and compiled patterns

    - Files: `engine/c_parser.py` (additions only).
    - Requirements: 3, criteria 1, 3 to 8, 13, 19.
    - Design: 1.3 (message constants and the pattern block), 1.2, C3.
    - Work: add the eight message constants (`NO_HANDLER`, `OUTSIDE`, `BOTH_REGISTERS`, `BLOCK_COMMENT`, `NESTED`, `STRAY_BRACE`, `HEADER_FORM`, `NOT_CLOSED`) with the exact text from design 1.3. Add the `W`, `FORM_ASSIGN`, `FORM_OR`, `FORM_AND`, `FORM_DECL`, `HANDLER_OPEN`, `HANDLER_EMPTY`, `RDR_WRITE`, `ISR_WRITE`, `REG_DECL_OTHER`, and `REG_NAME` patterns as raw strings, exactly as the fenced block in design 1.3.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      python3 -m ast engine/c_parser.py > /dev/null && echo AST_OK
      python3 -c "from engine.c_parser import REG_NAME, FORM_OR; print(REG_NAME.findall('UART_ISR = x; UART_RDR'), bool(FORM_OR.fullmatch('UART_ISR |= (1U << TX_DONE);')))"
      git diff --numstat engine/c_parser.py
      ```

      Expected: `AST_OK`; the print shows `['UART_ISR', 'UART_RDR'] True`; the `numstat` deletion count is 0.

  - [x] 1.2 Implement `_strip_comments`, `_scan_lines`, and `_reject_message`

    - Files: `engine/c_parser.py`.
    - Requirements: 3, criteria 9, 10, 13, 14, 16, 17, 18, 19.
    - Design: 1.3 (`_scan_lines` bullets, including the `REG_NAME` rule that tracks `first_reg` and `both_reported` inside a handler), 1.3 (`_reject_message` rules 1 to 5), C25.
    - Work: `_strip_comments(raw)` uses the same rule as the tokenizer. `_scan_lines(lines)` returns `(has_handler, errors)` where `errors` is a list of `(line, message)`. Follow the bullet order in design 1.3: blank line, block comment, `REG_NAME` check when inside, empty handler, handler open, closing brace, a line that starts with `void`, outside-handler statement, form match, and last the reject message. Add the unclosed-handler error after the loop. `_reject_message(code)` returns the first matching message from rules 1 to 5.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      python3 -c "from engine.c_parser import _scan_lines; print(_scan_lines(['void h(void) {', ' UART_ISR = (1U << TX_DONE);', ' uint8_t d = UART_RDR;', ' for (;;) {}', '}']))"
      ```

      Expected: `has_handler` is `True`, and the first error is `(3, BOTH_REGISTERS message)`. Line 4 is also reported, but it comes after line 3.

  - [x] 1.3 Implement `parse_user_snippet`

    - Files: `engine/c_parser.py`.
    - Requirements: 3, criteria 2, 14, 15, 17, 18, 20.
    - Design: 1.1 (signature, `_safe_line`), 1.3 Steps 1, 2, 3, and 5, Step 4 removed (the scan owns the two-register check), 1.5 (empty handler versus no handler), 1.6 (equivalence).
    - Work: `parse_user_snippet(snippet)` runs `parse()` in a try block. A `ParseError` becomes candidate `(_safe_line(e.line), 0, e.message)`. It then runs `_scan_lines(snippet.splitlines())`, and adds `(line, 2, message)` for each scan error. If there is no handler, it adds `(1, 1, NO_HANDLER)`. It raises `ParseError(line, message)` for the candidate with the smallest `(line, priority)`. Otherwise it returns the list from `parse()` unchanged.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      python3 -c "from engine.c_parser import parse_user_snippet as p; print(p('void h(void) {}'), end=' ')
      try: p('')
      except Exception as e: print(type(e).__name__, e.line, e.message)"
      ```

      Expected: `[]` followed by `ParseError 1 no handler definition: ...`.

  - [x] 1.4 Write unit tests for the error types, the precedence table, and the U+2028 divergence

    - Files: `tests/test_strict_parser.py` (new). Copy the four demo sources into this file as literals. Do not import `engine.demo`, because it imports cocotb.
    - Requirements: 3, criteria 1 to 20.
    - Design: 1.4 (all ten precedence rows), 1.7 (enforcement map), 7.1 (strict parser row, including the U+2028 case), C5, C25.
    - Work: one test per error type from 7.1 (loop, if/else, ternary, call, pointer, UART_RDR write, unknown register, unknown bit, RX_READY, raw constant, raw index, compound expression, `uint16_t`, no handler, empty text, statement outside a handler, both registers, block comment, header form, unclosed handler). One test per precedence row. The empty handler test expects `[]`. The U+2028 test: the snippet `void h(void) {`, a literal U+2028 character, ` UART_ISR = (1U << TX_DONE);`, another U+2028 character, and `}` is accepted, and its single WRITE op has `c_line == 2`. The same snippet with ` for (;;) {}` in place of the statement gives `ParseError` at line 2 with the loop message. Also test that the line of every raised error is an int of at least 1, and that the message is a str.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      pytest -q tests/test_strict_parser.py
      ```

      Expected: all tests pass.

  - [x] 1.5 Add property tests (Hypothesis)

    - Files: `tests/test_strict_parser.py`.
    - Requirements: 3, criterion 20.
    - Design: 7.1 (Hypothesis rows), 7.6 (P1 and P2), 7.7 (limits).
    - Work: property A: for any generated text, the result is either a list equal to `parse(text)`, or a `ParseError` with an int line of at least 1 and a str message. Property B: snippets built from the accepted forms (assignments, `|=`, `&=`, declarations, and one or more handlers) return the same list as `parse()` and never raise. Use `@settings(max_examples=100, deadline=None, derandomize=True)`, as in `tests/test_engine_props.py`.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      pytest -q tests/test_strict_parser.py -k property
      ```

      Expected: pass. These are randomized checks, so they are evidence, not proof (design 7.7).

  - [x] 1.6 Phase 1 regression gate

    - Files: none changed.
    - Work: confirm the existing engine tests still pass with their files unchanged.
    - Note: Requirements and Design links intentionally omitted (regression gate); traceability covers 39 of 40 subtasks.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      pytest -q tests/test_no_llm.py tests/test_engine_unit.py tests/test_engine_props.py
      git diff --stat -- tests/test_no_llm.py tests/test_engine_unit.py tests/test_engine_props.py
      ```

      Expected: all pass, and the `git diff` is empty.
## Phase 2: Replayed_State, BusDriver.peek, shared replay module, RTL tests

Decisions D2, D5, D7 apply. Design sections 2.1 to 2.7, 8.1, 8.3. Requirement 6 criterion 1, Requirement 8 criterion 8, and the Replayed_State glossary entry.

- [x] 2. Phase 2: replay path and real-RTL verification

  - [x] 2.1 Move the demo sources into `engine/snippets.py`

    - Files: `engine/snippets.py` (new), `engine/demo.py` (imports only).
    - Requirements: 2, criteria 1 and 4; 6, criterion 10.
    - Design: 8.1, D7, C2.
    - Work: before editing, record the baseline hash of the four demo source constants. Create `engine/snippets.py` with `DEMO_SNIPPET_NAMES`, the four source constants (byte-identical), and `DEMO_SOURCES`, a tuple of `(name, source)` pairs in order. In `engine/demo.py`, replace the constant definitions with imports from `engine.snippets`. Keep `PRE_HW_SET` and the replay functions in `engine/demo.py`.
    - Verification (the hash must match before and after):

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      python3 -c "import ast,hashlib; t=ast.parse(open('engine/snippets.py',encoding='utf-8').read()); v=[n.value.value for n in t.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str) and n.targets[0].id.endswith('SNIPPET')]; print(len(v), hashlib.sha256(''.join(v).encode()).hexdigest())"
      python3 -m ast engine/demo.py > /dev/null && echo AST_OK
      ```

      Expected: `4` and the same hash as the baseline recorded before the move. Then run the cocotb `test_demo` module (task 2.9) to confirm the import still works.

  - [x] 2.2 Implement `engine/replayed_state.py` and its unit tests

    - Files: `engine/replayed_state.py` (new), `tests/test_replayed_state.py` (new).
    - Requirements: Replayed_State glossary entry; 6, criterion 7; 8, criterion 4.
    - Design: 2.1 (shape, `REGISTER_MAX`, `make_replayed_state`, `validate_replayed_state`, `isr_replayed_state`, `rdr_replayed_state`), 7.1 (`test_replayed_state.py` row).
    - Work: implement the four functions exactly as design 2.1. `isr_replayed_state` returns `None` when no WRITE or RMW entry exists, and otherwise takes `pre` from `accesses[0]` and `post` from `accesses[-1]`. Tests cover: empty accesses give None; reads only give None; write pre and post; a read followed by a write takes pre from the read; RMW; `rdr_replayed_state`; `validate_replayed_state` rejects bool values, UART_ISR pre 16, UART_RDR post 256, and wrong keys; accepts None.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      pytest -q tests/test_replayed_state.py
      ```

      Expected: all pass. This module must not import cocotb (D7).

  - [x] 2.3 Add `BusDriver.peek` to `engine/bus_driver.py`

    - Files: `engine/bus_driver.py` (addition only). The `tests/bus_driver.py` path in the request does not exist. `BusDriver` is in `engine/`, which is where design 2.4 puts it.
    - Requirements: 6, criterion 7; Replayed_State glossary entry (post is measured, never assumed).
    - Design: 2.4 (`peek` code and the RTL citation to `rtl/uart_ctrl.sv` lines 26 to 28), D5.
    - Work: add the `async def peek(self, addr)` method exactly as design 2.4. It must not assert `re` or `we`.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      python3 -m ast engine/bus_driver.py > /dev/null && echo AST_OK
      git diff --numstat engine/bus_driver.py
      ```

      Expected: `AST_OK`, and the deletion count is 0. The behavior is checked on the RTL in task 2.9.

  - [x] 2.4 Record ISR accesses in `run_c_source` (`engine/demo.py`)

    - Files: `engine/demo.py`.
    - Requirements: Replayed_State glossary entry (UART_ISR pre and post); 8, criterion 4.
    - Design: 2.2, C14, C15. Keep the signature and the `trace["ops"]` content.
    - Work: record every access in order, including READ accesses (use the value returned by `bus.read`). Set `trace["accesses"]` and `trace["replayed_state"] = isr_replayed_state(accesses)`.
    - Verification: run the existing cocotb `test_demo` module (task 2.9). All 13 tests must still pass.

  - [x] 2.5 Add the RDR probe, `rx_on_read`, and `replayed_state` to `run_c_rdr_source` (`engine/demo.py`)

    - Files: `engine/demo.py`.
    - Requirements: Replayed_State glossary entry (RDR post is measured from the RTL); 6, criterion 7.
    - Design: 2.3 (`post_probe`, `rx_on_read`, `pre = reads[0].value`, `post = await post_probe()`), 2.6 (RTL citations: `rtl/uart_ctrl.sv` line 47), C16. Defaults keep today's behavior.
    - Work: when `rx_on_read` is set, skip the standard pulse and drive `rx_valid=1` and `rx_data` during the commit edge of the last read only. Never replace `post` with 0 or with `pre`.
    - Verification: run the cocotb `test_demo` module again (task 2.9). All 13 tests must still pass. Then run `python3 -m engine.demo run > /dev/null && echo DEMO_RUN_OK` from the repository root; it must print `DEMO_RUN_OK`.

  - [x] 2.6 Create the shared replay module `tests/snippet_run.py`

    - Files: `tests/snippet_run.py` (new).
    - Requirements: 6, criterion 1; 8, criterion 8 (the module never writes the Snapshot).
    - Design: 2.5 (dispatch, quiet runs), 2.7, 8.2 (the old `REGSPECTRE_DEMO_OUT` mechanism is removed with `tests/demo_print.py` in task 3.3).
    - Work: a cocotb module with one `@cocotb.test()` coroutine. It reads `REGSPECTRE_RUN_IN` (JSON `{"runs": [...]}`), calls `BusDriver.start()`, replays each run with `parse()` dispatch, and writes `REGSPECTRE_RUN_OUT` with the records in the form `{"records": [{"name", "source", "report", "replayed_state"}]}`. The module name must not start with `test_`.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      python3 -m ast tests/snippet_run.py > /dev/null && echo AST_OK
      python3 -m engine.demo run > /dev/null && echo DEMO_RUN_OK
      ```

      Expected: `AST_OK` and `DEMO_RUN_OK`.

  - [x] 2.7 Write the real-RTL tests `tests/test_replayed_rtl.py`

    - Files: `tests/test_replayed_rtl.py` (new).
    - Requirements: Replayed_State glossary entry; 8, criteria 4 and 5.
    - Design: 2.6 (negative control, scenarios A and B, the `assert_rdr_post` helper, the broken probes `assume_zero` and `assume_pre`), 7.3 (the seven tests and their expected values), and the O5 guardrail in 7.3.
    - Work: exactly seven tests. Six are value tests: `test_isr_rmw_replayed_state` (pre 9, post 0), `test_isr_direct_replayed_state` (pre 9, post 8), `test_isr_read_only_replayed_state_is_null` (null, report `[]`), `test_rdr_double_read_replayed_state` (pre 165, post 0), `test_rdr_single_read_replayed_state` (pre 165, post 0), `test_rdr_post_measured_after_rx_on_read` (pre 0, post 60). The seventh is `test_rdr_post_negative_control`, which runs both broken probes and asserts `AssertionError` in each. The module defines only `@cocotb.test()` coroutines and helpers whose names do not start with `test_` (O5 guardrail).
    - Verification: task 2.9.

  - [x] 2.8 Update `tests/Makefile`

    - Files: `tests/Makefile` (one line only).
    - Requirements: Replayed_State glossary entry (the RTL tests run in the default target).
    - Design: 8.3, 7.3.
    - Work: on the uart_ctrl branch, append `,test_replayed_rtl` to the `COCOTB_TEST_MODULES` line. Leave the smoke branch, the `PYTHONPATH` export, and the `include` line unchanged. The default count goes from 33 to 40.
    - Verification:

      ```bash
      cd /home/hashir/regspectre
      git diff -- tests/Makefile
      ```

      Expected: exactly one changed line, and it adds `,test_replayed_rtl` to the uart_ctrl `COCOTB_TEST_MODULES` line.

  - [x] 2.9 First real RTL run and confirmation of the seven derived values

    - Files: none changed. Results are recorded in the task notes.
    - Requirements: Replayed_State glossary entry; 8, criterion 4.
    - Design: 7.3 (values are derived from `rtl/uart_ctrl.sv` and not yet confirmed), 2.4 and 2.6 (RTL citations).
    - Work: run the default target and the existing `test_demo` module, and record every Replayed_State value that the seven tests print. If any value differs from the 7.3 table, stop, find the cause in the test or the RTL, and report it. Do not change an expected value to match a run without an explanation.
    - Verification:

      ```bash
      cd /home/hashir/regspectre/tests && source /home/hashir/.venv/bin/activate
      make COCOTB_TEST_MODULES=test_demo 2>&1 | tee /tmp/make_demo.log
      make 2>&1 | tee /tmp/make_default.log
      grep -E "TESTS=|FAIL" /tmp/make_default.log | tail -n 5
      ```

      Expected: `test_demo` passes all 13 tests. The default target runs 40 tests (33 existing and 7 new), and all pass once the seven values are confirmed.

  - [x] 2.10 O5 guardrail: collection and full pytest run

    - Files: none changed.
    - Requirements: none directly; this protects the existing test layout.
    - Design: 7.3 (guardrail), 10 (O5), 7.7 (limits).
    - Work: confirm that pytest collects `tests/` cleanly with no config file present. Record the result of the full run. Cocotb-style modules that fail under pytest are recorded, not hidden.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      ls pytest.ini pyproject.toml setup.cfg 2>/dev/null || echo NO_PYTEST_CONFIG
      pytest --collect-only -q tests/ 2>&1 | tail -n 3
      pytest -q tests/ 2>&1 | tail -n 15
      ```

      Expected: `NO_PYTEST_CONFIG`; collection has no errors; the full run result is recorded.

## Phase 3: Snapshot writer, replay runner, and Demo CLI

Decisions D6 and D7 apply. Design sections 3.1 to 3.2, 4, 8.2. Requirement 8 criteria 1 to 8.

- [x] 3. Phase 3: engine Snapshot and runner

  - [x] 3.1 Implement `engine/snapshot.py` and its tests

    - Files: `engine/snapshot.py` (new), `tests/test_snapshot.py` (new).
    - Requirements: 8, criteria 1 to 8.
    - Design: 3.1 (schema), 3.2 (`REPO_ROOT`, `SNAPSHOT_PATH`, `build_snapshot`, `write_snapshot_atomic`), 7.1 (`test_snapshot.py` row), P3.
    - Work: `build_snapshot` validates the names and their order, the keys of each record, `source` as a string, `report` as a JSON list text, `replayed_state` through `validate_replayed_state`, and the `created_utc` format. It raises `ValueError` and does not touch the disk. `write_snapshot_atomic` writes the text to `path.with_name(path.name + ".tmp")` with LF endings, runs `flush` and `fsync`, then `os.replace`. On any exception it removes the temp file and re-raises. The literal `demo_snapshot.json` appears only in this file.
    - Tests: schema and order; wrong names rejected; success writes the exact text; `os.replace` monkeypatched to raise keeps the old bytes and removes the temp file; invalid records leave the existing file untouched; a missing file stays missing; the literal check.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      pytest -q tests/test_snapshot.py
      grep -rln "demo_snapshot.json" engine backend tests web/lib 2>/dev/null
      ```

      Expected: the tests pass. The `grep` lists only `engine/snapshot.py`, with no other file.

  - [x] 3.2 Implement `engine/sim_runner.py` and its tests

    - Files: `engine/sim_runner.py` (new), `tests/test_sim_runner.py` (new), `.gitignore` (one line added).
    - Requirements: 7, criteria 1, 3, and 8; 6, criterion 2; 8, criterion 7.
    - Design: 4 (the full `run_replays` procedure, steps 1 to 9, and `flock_held`), D6, C10, C18.
    - Work: implement `MAKE_COMMAND`, `TESTS_DIR`, `LOCK_PATH` (`tests/.sim.lock`), `SIM_MODULE = "snippet_run"`, the three exception classes, `run_replays`, and `flock_held`. Use `start_new_session=True`. Send output to temp files, not pipes. On timeout, send SIGTERM to the process group, wait 5 seconds, then SIGKILL if needed. Validate the output records against `runs`. Add `tests/.sim.lock` to `.gitignore` (design C18).
    - Tests (with `MAKE_COMMAND` replaced by a fake script): success writes and reads the result; a non-zero exit gives `SimulationFailed` with the last stderr line; a timeout kills the whole process group, and a child sleep started by the fake script is gone afterwards; a held lock gives `SimulationBusy`; the lock is free again after each case.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      pytest -q tests/test_sim_runner.py
      python3 -c "import engine.sim_runner as s; print(s.SIM_MODULE, s.LOCK_PATH.name)"
      git check-ignore -v tests/.sim.lock
      ```

      Expected: tests pass. The print shows `snippet_run .sim.lock`, and `git check-ignore -v` prints the `.gitignore` line that matches `tests/.sim.lock`.

  - [x] 3.3 Update `engine/demo.py` to use the runner and the Snapshot writer

    - Files: `engine/demo.py`, `tests/demo_print.py` (deleted; approved as O3, D2, C2).
    - Requirements: 8, criteria 1, 2, 4, 5, 7 and 8; 6, criterion 1.
    - Design: 8.2 (the `run` path and exit codes), C17, D2.
    - Work: `run_demo()` builds `runs` from `DEMO_SOURCES`, calls `run_replays(runs, timeout_s=None)`, validates the records, calls `build_snapshot` and then `write_snapshot_atomic(SNAPSHOT_PATH, ...)`, and then prints the records in the existing format. A busy lock prints "another simulation is running" and exits with status 1. A failed replay prints the message and exits with status 1, without writing. The no-argument usage stays unchanged. After `engine/demo.py` uses `run_replays` and `engine/snapshot.py`, remove its three `demo_print` references (the comment above `DEMO_OUTPUT_ENV`, the `DEMO_COCOTB_MODULE` assignment, and the module name in the docstring that describes the make call), then delete `tests/demo_print.py`.
    - Check first: plain Python must be able to import `engine.demo`. `engine/demo.py` imports `engine/bus_driver.py`, which imports cocotb, so this import is not yet verified outside the simulator. If the import fails, move the cocotb imports into the replay functions and report the change.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      python3 -c "import engine.demo; print('IMPORT_OK')"
      python3 -m engine.demo; echo exit=$?
      python3 -m ast engine/demo.py > /dev/null && echo AST_OK
      test ! -e tests/demo_print.py && echo DELETED
      grep -rn "demo_print" engine tests backend web 2>/dev/null || echo NO_REFERENCES
      ```

      Expected: `IMPORT_OK`, the usage text with `exit=0`, `AST_OK`, `DELETED`, and `NO_REFERENCES`.

  - [x] 3.4 Generate `web/public/demo_snapshot.json` through the engine

    - Files: `web/public/demo_snapshot.json` (written by the engine only; never edited by hand).
    - Requirements: 8, criteria 1 to 5.
    - Design: 3.1, 8.2, D6.
    - Work: run the demo CLI once, with the simulator available and no other simulation running. Then check the file: top-level keys, `created_utc` format, four records in order, each report is a string that parses as a JSON array, and each `replayed_state` matches the values confirmed in task 2.9.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      python3 -m engine.demo run > /tmp/demo_run.log; echo exit=$?
      python3 -c "import json,re; d=json.load(open('web/public/demo_snapshot.json',encoding='utf-8')); assert list(d)==['created_utc','records']; assert re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', d['created_utc']); assert [r['name'] for r in d['records']]==['ISR_RMW_SNIPPET','ISR_DIRECT_SNIPPET','RDR_DOUBLE_READ_SNIPPET','RDR_SINGLE_READ_SNIPPET']; assert all(isinstance(json.loads(r['report']),list) for r in d['records']); print('SNAPSHOT_OK', [r['replayed_state'] for r in d['records']])"
      ```

      Expected: `exit=0` and `SNAPSHOT_OK` followed by the four replayed states.

  - [x] 3.5 Confirm the Snapshot is not touched by any other path

    - Files: none changed.
    - Requirements: 6, criterion 2; 8, criteria 7 and 8.
    - Design: 3.2 (guarantees), 5.7, 7.2 (the Snapshot-untouched test).
    - Work: check that only the demo run path writes the file. Run the Backend tests, which patch the Snapshot path to a temp file, and confirm the real file's hash does not change.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      sha256sum web/public/demo_snapshot.json > /tmp/snap_before.txt
      pytest -q tests/test_backend_api.py -k snapshot
      sha256sum -c /tmp/snap_before.txt
      ```

      Expected: the `sha256sum -c` line reports OK. This task depends on Phase 4.

## Phase 4: Local FastAPI Backend (`backend/`)

Decisions D1, D3, D6 apply. Design sections 5.1 to 5.7, 7.2, 7.5. Requirement 3 criteria 21 to 25, Requirement 6 criteria 1 to 11, Requirement 7 criteria 1 to 3 and 8.

- [x] 4. Phase 4: Backend in `backend/`, bound to 127.0.0.1 only

  - [x] 4.1 Create `backend/requirements.txt` and install the packages into `~/.venv`

    - Files: `backend/requirements.txt` (new).
    - Requirements: 6, criteria 3 and 9.
    - Design: 5.1 (dependency list, and the note that httpx is not installed in `~/.venv`, which is reported), D1.
    - Work: create the file with `fastapi`, `uvicorn`, and `httpx`, one per line. Then install them into the venv. Install `httpx` before running any Backend API test, because `TestClient` needs it.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      cat backend/requirements.txt
      pip install -r backend/requirements.txt
      python3 -c "import fastapi, uvicorn, httpx; print('DEPS_OK', fastapi.__version__, uvicorn.__version__, httpx.__version__)"
      ```

      Expected: the three package names are listed, the install finishes without errors, and `DEPS_OK` prints with three versions.

  - [x] 4.2 Implement `backend/__init__.py` and `backend/validation.py`

    - Files: `backend/__init__.py` (empty, new), `backend/validation.py` (new). This module imports no FastAPI.
    - Requirements: 3, criteria 21, 22, 24, 25; 6, criteria 4, 5, 6.
    - Design: 5.4 (Steps 1 to 3, the `count_lines` rule, the order and the RunRequest), 5.3 (the body rules), C6, C7, C24, D3.
    - Work: implement `count_lines(text)` with the four steps from design 5.4: empty gives 0; replace `\r\n`, then `\r`, with `\n`; remove one trailing `\n`; split on `\n` only and return the number of parts. Do not use `splitlines`. Implement `validate_run_request(raw: bytes)`, which returns `RunRequest` or `ErrorReply`. Step 1 is too_large (more than 8192 UTF-8 bytes, or `count_lines` above 200). Step 2 is invalid_request (not JSON, not an object, keys not exactly one of the two, unknown name, `c_source` not a string, extra keys). Step 3 is parser_error (calls `parse_user_snippet`). Define `RunRequest.as_run()`, which returns `[{"name", "source"}]`.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      python3 -m ast backend/validation.py > /dev/null && echo AST_OK
      python3 -c "from backend.validation import count_lines as c; print(c(''), c('x'), c('x\n'), c('x\r\n'), c('x\n\n'), c('a\u2028b'))"
      ```

      Expected: `AST_OK`, then `0 1 1 1 2 1`.

  - [x] 4.3 Write the count-line tests `tests/test_count_lines.py`

    - Files: `tests/test_count_lines.py` (new).
    - Requirements: 3, criteria 24 and 25.
    - Design: 7.1 (`test_count_lines.py` row), 5.4, and the U+2028 note in 1.3.
    - Work: the Python cases from 7.1: empty gives 0; `x` gives 1; a trailing `\n` gives 1; `\r\n` gives 1; a lone `\r` gives 1; `\n\n` gives 2; U+2028 between two words gives 1; 200 lines gives 200 and is accepted; 201 lines gives 201 and is rejected by `validate_run_request` as too_large. Include one test where a literal U+2028 separates two lines of an otherwise valid snippet: `count_lines` gives 1, while `parse_user_snippet` still reports the write at c_line 2 (the intended divergence from design 1.3).
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      pytest -q tests/test_count_lines.py
      ```

      Expected: all pass.

  - [x] 4.4 Implement `backend/app.py`

    - Files: `backend/app.py` (new).
    - Requirements: 6, criteria 1 to 11; 7, criteria 1 to 3 and 8; 3, criteria 21 and 22.
    - Design: 5.2 (binding, CORS), 5.3 (endpoints and error bodies), 5.5 (the handler, `SIM_LOCK`, the lock release in `finally`, `one_line`), 5.6 (timeout), 5.7 (single worker).
    - Work: create the FastAPI app with `CORSMiddleware` for exactly `http://localhost:3000` and `http://127.0.0.1:3000`. Routes: `GET /api/status` returns `{"busy": SIM_LOCK.locked() or flock_held()}`. `GET /api/snippets` returns the four entries in `DEMO_SNIPPET_NAMES` order from `engine/snippets.py`. `POST /api/run` reads the raw body, runs `validate_run_request`, takes `SIM_LOCK` without blocking (409 on failure), calls `run_replays` in a thread with `RUN_TIMEOUT_S = 60.0`, maps the exceptions to 409, 504, or 500, and releases `SIM_LOCK` in `finally`. Do not use a Pydantic body model. The binding address is 127.0.0.1 only. Do not write any code that binds to all interfaces.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      python3 -m ast backend/app.py > /dev/null && echo AST_OK
      python3 -c "import backend.app as a; print([r.path for r in a.app.routes if hasattr(r, 'path')])"
      grep -n "0.0.0.0" backend/app.py || echo NO_WILDCARD_BIND
      ```

      Expected: `AST_OK`, the route list includes `/api/status`, `/api/snippets`, and `/api/run`, and `NO_WILDCARD_BIND`.

  - [x] 4.5 Write the Backend API tests `tests/test_backend_api.py`

    - Files: `tests/test_backend_api.py` (new). Requires `httpx` from task 4.1.
    - Requirements: 6, criteria 1 to 11; 7, criteria 1 to 3 and 8; 3, criteria 21, 22, 24, 25.
    - Design: 7.2 (every bullet: order matrix, busy, status, snippets, success shape, timeout, failure message, busy from the runner, unexpected error with lock release, invalid bodies, CORS, Snapshot untouched, `0.0.0.0` absent, boundaries), P4.
    - Work: replace `run_replays` with fakes. Patch `engine.snapshot.SNAPSHOT_PATH` to a temp file.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      pytest -q tests/test_backend_api.py
      ```

      Expected: all pass.

  - [x] 4.6 Write the Backend static check `tests/test_backend_no_llm.py`

    - Files: `tests/test_backend_no_llm.py` (new). It imports the scanner from `tests/test_no_llm.py` and leaves that file unchanged.
    - Requirements: 6, criterion 8.
    - Design: 5.7, 7.5, D1.
    - Work: scan every `.py` file under `backend/` with the forbidden-name rules. Assert no import and no eval or exec call is found.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      pytest -q tests/test_backend_no_llm.py tests/test_no_llm.py
      ```

      Expected: all pass, and `tests/test_no_llm.py` is unchanged (`git diff --stat -- tests/test_no_llm.py` is empty).

  - [x] 4.7 Manual smoke check of the Backend (user terminal)

    - Files: none changed.
    - Requirements: 6, criteria 3, 4, 5, 10, 11.
    - Design: 5.2, 5.3, D8.
    - Work: the user starts the Backend in a separate terminal, bound to 127.0.0.1 and port 8000 by calling uvicorn with those values in code, not with command-line flags. The agent does not start the server. Then check the endpoints with the commands below.
    - Start (user terminal, from the repository root, venv active):

      ```bash
      python3 -c "import uvicorn; uvicorn.run('backend.app:app', host='127.0.0.1', port=8000, workers=1)"
      ```

    - Check (second terminal):

      ```bash
      curl -s http://127.0.0.1:8000/api/status
      curl -s http://127.0.0.1:8000/api/snippets | head -c 300; echo
      curl -s -X POST http://127.0.0.1:8000/api/run -H "Content-Type: application/json" -d "{\"snippet\":\"NOT_A_NAME\"}"; echo
      ```

      Expected: `{"busy":false}`; the four snippet names in order; and `{"error":"invalid_request"}`.

## Phase 5: Studio UI (`web/`)

Decisions D2 and D8 apply. Design sections 6.1 to 6.18, 7.4, 7.5. Requirements 1 to 10 (Studio side). The Studio never calls the Backend except through `BACKEND_URL` (design 6.15).

- [ ] 5. Phase 5: Next.js Studio with pure logic first, then components

  - [x] 5.1 Scaffold the Next.js app and the test tooling

    - Files: `web/package.json`, `web/tsconfig.json`, `web/next.config.mjs`, `web/vitest.config.ts`, `web/app/layout.tsx`, `web/app/page.tsx`.
    - Requirements: 1, criteria 1 to 4.
    - Design: 6.1 (stack and file list), C22 (no package version is fixed by the design; the exact versions are chosen here and recorded in `package.json`).
    - Work: use the App Router with TypeScript. Add Vitest, React Testing Library, and jsdom as dev dependencies. Make `page.tsx` render `StudioPage` as a client component.
    - Verification:

      ```bash
      cd /home/hashir/regspectre/web
      node -v && npm -v
      npm install
      npx tsc --noEmit && echo TSC_OK
      npx vitest run --passWithNoTests && echo VITEST_OK
      npm run build && echo BUILD_OK
      ```

      Expected: each step prints its `_OK` line.

  - [x] 5.2 Add config, types, and the exact message strings

    - Files: `web/lib/config.ts`, `web/lib/types.ts`, `web/lib/messages.ts`.
    - Requirements: 7, criteria 6, 8, 9, 10; 9, criteria 3, 5, 8, 9 and 13; 10, criteria 1 to 5, 10 and 11; 1, criteria 3 and 6; 3, criteria 23 and 24; 5, criterion 15; 4, criterion 5.
    - Design: 6.15 (constants), 6.16 (every message constant), 6.13 (the disclaimer names `DISCLAIMER_1` to `DISCLAIMER_5` and `REPLAYED_NOTE_1` and `REPLAYED_NOTE_2`).
    - Work: copy every message from design 6.16 and every disclaimer from Requirement 10 word for word. This file is the only place they live.
    - Verification: each of the following must print a match. Run one `grep -F` per message, for example:

      ```bash
      cd /home/hashir/regspectre/web
      grep -F "No response arrived within 70 seconds. The Backend may still be running the simulation. No results are shown." lib/messages.ts
      grep -F "Waveform view is not available in this version." lib/messages.ts
      grep -F "Replayed state is the state of the replayed snippet in the uart_ctrl simulation. It is not the state of a whole chip." lib/messages.ts
      grep -F "Hardware noise that arrives between the pre sample and the commit is not in pre." lib/messages.ts
      ```

      Expected: each `grep` prints the line that holds the exact text.

  - [x] 5.3 Implement the shared reader `web/lib/reader.ts` and its tests

    - Files: `web/lib/reader.ts` (new), `web/__tests__/reader.test.ts` (new).
    - Requirements: 8, criterion 6; 9, criterion 4; 6, criterion 7; 8, criterion 16.
    - Design: 6.2 (`parseReportText`, `parseReplayedState`, `parseRunBody`, `parseSnapshot`, `parseSnippetList`, `parseErrorResponse`), 6.2 note on 409 and 504 bodies, 7.4 (the `reader.test.ts` row). C12, C13.
    - Work: each function returns `{ok: true, value}` or `{ok: false}` and never throws. `parseErrorResponse` returns the unreadable reply for a 409 body other than busy and for a 504 body other than timeout, and for every other unexpected body that design 6.5 maps to `CANNOT_READ`.
    - Verification:

      ```bash
      cd /home/hashir/regspectre/web
      npx vitest run __tests__/reader.test.ts
      ```

      Expected: all tests pass, including the 409 and 504 cases with other bodies.

  - [x] 5.4 Implement `countLines` and the demo derivation `web/lib/snippetState.ts` and its tests

    - Files: `web/lib/snippetState.ts` (new), `web/__tests__/snippetState.test.ts` (new).
    - Requirements: 2, criteria 5, 6 and 7; 3, criterion 24.
    - Design: 5.4 (the `count_lines` rule, which `countLines` must match exactly), 6.7 (`demoNameFor`, `runBody`, `countLines`), 7.4 (the `snippetState.test.ts` row), 1.3 (U+2028 note).
    - Work: `countLines` uses the four steps from design 5.4 and returns `text.split("\n").length` after the normalization. It must not use a line-splitting method that also splits on U+2028.
    - Tests: the same inputs and results as `tests/test_count_lines.py` (task 4.3), including a U+2028 between two words giving 1; exact equality for the demo derivation; one changed character makes a user snippet; run body shapes; the size limit at exactly 200 and 201 lines, and at 8192 and 8193 bytes.
    - Verification:

      ```bash
      cd /home/hashir/regspectre/web
      npx vitest run __tests__/snippetState.test.ts
      ```

      Expected: all tests pass.

  - [x] 5.5 Implement the 32-cell model `web/lib/registerCells.ts` and its tests

    - Files: `web/lib/registerCells.ts` (new), `web/__tests__/registerCells.test.ts` (new).
    - Requirements: 5, criteria 1 to 16.
    - Design: 6.10 (`buildRegisterCells` rules), 7.4 (the `registerCells.test.ts` row).
    - Work: implement `buildRegisterCells(register, shown)` as a pure function, following 6.10 step by step.
    - Verification:

      ```bash
      cd /home/hashir/regspectre/web
      npx vitest run __tests__/registerCells.test.ts
      ```

      Expected: all tests pass. The tests check that unused cells never contain 0, 1, a violation, a replayed value, or "no violation reported".

  - [ ] 5.6 Implement the outcome mapping `web/lib/runState.ts` and its tests

    - Files: `web/lib/runState.ts` (new), `web/__tests__/runState.test.ts` (new).
    - Requirements: 7, criteria 6 to 10; 8, criteria 11, 12, 14, 15, 16; 9, criteria 3 to 13; 3, criteria 23 and 24.
    - Design: 6.5 (the `Shown` type, the routing table, and the full outcome table, including the 409 and 504 other-body rows), 7.4 (the `runState.test.ts` row). Design 6.5 shows the recorded path only when the Backend is unreachable.
    - Work: implement `startRun` (pending on, shown empty), the routing function, and the outcome function. The outcome function returns a `Shown` value for each row of the table.
    - Verification:

      ```bash
      cd /home/hashir/regspectre/web
      npx vitest run __tests__/runState.test.ts
      ```

      Expected: every row of the 6.5 table has a passing test. Error bodies never produce a `recorded` result.

  - [ ] 5.7 Implement the client `web/lib/api.ts` and the poller `web/lib/poller.ts` and their tests

    - Files: `web/lib/api.ts` (new), `web/lib/poller.ts` (new), `web/__tests__/poller.test.ts` (new).
    - Requirements: 7, criteria 4, 5 and 6; 8, criteria 10 and 14.
    - Design: 6.3 (`fetchStatus`, `postRun`, `fetchSnippets`, `loadSnapshot`, AbortController with `setTimeout`), 6.4 (polling, `unknown` until the first outcome), C21, 7.4 (the `poller.test.ts` row, fake timers).
    - Work: the poller waits for each outcome before it schedules the next. The next request starts 1000 ms after the previous start. A request that is aborted at 2000 ms gives `unreachable`. Any HTTP response gives `reachable`.
    - Verification:

      ```bash
      cd /home/hashir/regspectre/web
      npx vitest run __tests__/poller.test.ts
      ```

      Expected: all tests pass.

  - [ ] 5.8 Implement source loading `web/lib/sources.ts`

    - Files: `web/lib/sources.ts` (new).
    - Requirements: 2, criteria 1, 3, 7, 8, 9 and 10.
    - Design: 6.6 (fetch the list, then fill missing names from the Snapshot, with the whole-file rule in C13), 6.17.
    - Work: `fetchSnippets` first, then `loadSnapshot` and `parseSnapshot` for each name still missing. If the selected name has no source, the code pane shows `SOURCES_UNAVAILABLE`.
    - Verification: design 7.4 has no dedicated test for this module. Cover it in task 5.11 (the manual smoke check). Note this gap in the task report.

  - [ ] 5.9 Implement the components and the page layout

    - Files: `web/components/CodePane.tsx`, `web/components/SnippetSelector.tsx`, `web/components/RunControl.tsx`, `web/components/RegisterArray.tsx`, `web/components/ViolationList.tsx`, `web/components/WaveformPlaceholder.tsx`, `web/components/Disclaimers.tsx`, `web/components/Message.tsx`, `web/app/StudioPage.tsx` (new). The files in `web/components/` and `web/app/StudioPage.tsx` are new.
    - Requirements: 1, criteria 1 to 7; 2, criteria 1 to 6; 4, criteria 1 to 7; 5, criteria 1 to 16; 7, criteria 4 and 5; 10, criteria 1 to 11.
    - Design: 6.8 (run control rule), 6.11 (violation list and the source label, which is the recorded-output banner the request asked for), 6.12 (message area), 6.13 (disclaimers, always rendered), 6.14 (layout and the waveform slot as a fixed grid area), 6.9 (no "live" text in recorded view).
    - Work: `RunControl` enabled only by the rule in 6.8. `RegisterArray` has the register selector (UART_ISR first), 32 cells, and the violation mark text. `WaveformPlaceholder` renders only `WAVEFORM_PLACEHOLDER`, with no inputs and no buttons. `StudioPage` owns the state and wires the poller, sources, and run flow.
    - Note: the request also asked for "reserved Tier 2/3 placeholders". Design 6.14 defines only the waveform slot, and no Tier 2 or Tier 3 is named in the design or the requirements. This task builds only the waveform slot. See the open items at the end of this file.
    - Verification:

      ```bash
      cd /home/hashir/regspectre/web
      npx tsc --noEmit && echo TSC_OK
      npm run build && echo BUILD_OK
      ```

      Expected: both `_OK` lines print.

  - [ ] 5.10 Component tests for disclaimers, recorded text, and the violation list

    - Files: `web/__tests__/disclaimers.test.tsx`, `web/__tests__/recordedText.test.tsx`, `web/__tests__/violationList.test.tsx` (all new).
    - Requirements: 10, criteria 1 to 11; 8, criterion 13; 4, criteria 1 to 7; 1, criteria 5 to 7.
    - Design: 7.4 (the three rows), 6.9 (the case-insensitive test for "live").
    - Work: the disclaimers test checks that the five texts are always rendered and that the two replayed notes appear only when replayed state is shown. The recorded test renders recorded output and fails if any text node matches `/live/i`. The violation list test checks the source label for live and recorded, the empty text, "not from C", and row order.
    - Verification:

      ```bash
      cd /home/hashir/regspectre/web
      npx vitest run __tests__/disclaimers.test.tsx __tests__/recordedText.test.tsx __tests__/violationList.test.tsx
      ```

      Expected: all pass.

  - [ ] 5.11 Static check of the Studio source `tests/test_web_static.py`

    - Files: `tests/test_web_static.py` (new).
    - Requirements: 6, criterion 9 (the localhost origins); 10, criterion 7 is not affected.
    - Design: 7.5, 6.18.
    - Work: scan `web/` source files (`.ts`, `.tsx`, `.mjs`, `.js`) for absolute `http://` or `https://` URLs. Only `BACKEND_URL` in `web/lib/config.ts` and the two localhost origins are allowed. Skip `node_modules`, `.next`, and generated files.
    - Verification:

      ```bash
      cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
      pytest -q tests/test_web_static.py
      ```

      Expected: all pass.

  - [ ] 5.12 Final local end-to-end verification checklist

    - Files: none changed.
    - Requirements: all ten requirements.
    - Design: all sections; D8 (local only).
    - Work: run the checklist in order. Record each result. Stop at the first failure and report it.
    - Checklist:
      1. Python suites, from the repository root:

         ```bash
         cd /home/hashir/regspectre && source /home/hashir/.venv/bin/activate
         pytest -q tests/test_strict_parser.py tests/test_count_lines.py tests/test_replayed_state.py tests/test_snapshot.py tests/test_sim_runner.py tests/test_backend_api.py tests/test_backend_no_llm.py tests/test_web_static.py tests/test_no_llm.py tests/test_engine_unit.py tests/test_engine_props.py
         ```

      2. The existing demo module on the RTL, then the default cocotb target with 40 tests:

         ```bash
         cd /home/hashir/regspectre/tests && source /home/hashir/.venv/bin/activate
         make COCOTB_TEST_MODULES=test_demo 2>&1 | tail -n 3
         make 2>&1 | tee /tmp/make_final.log
         grep -E "TESTS=|FAIL" /tmp/make_final.log | tail -n 5
         ```

      3. Snapshot regeneration and check (task 3.4) and the Snapshot-untouched check (task 3.5).

      4. Studio unit and component tests, the type check, and the build:

         ```bash
         cd /home/hashir/regspectre/web
         npx vitest run
         npx tsc --noEmit && npm run build
         ```

      5. Local smoke check, with the user starting both servers in separate terminals. The Backend start command is in task 4.7. Start the Next.js development server from the `web` folder with `npm run dev`. Then open the local Studio page in a browser. Check that: the four demo names appear in order; ISR_RMW_SNIPPET is selected; the disclaimers are visible; the waveform slot shows its placeholder text; a Run on the ISR_RMW snippet shows a live result with the source label "Live result". Then stop the Backend and check that the Studio shows the recorded output for the ISR_RMW snippet with the label "Recorded output, created" followed by the Snapshot time, and that no word "live" appears in that view.

    - Expected: each step passes. The final report lists the result of every step.

## Notes

The open items at the end of this file list the points the implementer must settle before or during the work.

## Decision traceability

| Decision | Tasks |
|---|---|
| D1 Backend in `backend/`, outside `engine/` | 4.1, 4.2, 4.6 |
| D2 One shared replay module; `tests/demo_print.py` retired | 2.6, 3.3 |
| D3 Check order: too_large, invalid_request, parser_error, busy | 4.2, 4.4, 4.5 |
| D4 Strict parser is `parse()` plus a per-line matcher | 1.1 to 1.5 |
| D5 RDR post sampled with `BusDriver.peek` | 2.3, 2.5, 2.9 |
| D6 Threading lock plus `flock` on `tests/.sim.lock` | 3.2, 3.3, 4.4 |
| D7 Pure modules do not import cocotb | 2.2, 3.1, 3.2, 4.2 |
| D8 Local 127.0.0.1 only; deployment out of scope | 4.4, 4.6, 4.7, 5.11, 5.12 |

## Design coverage check

| Design section | Tasks |
|---|---|
| 1 Strict parser (1.1 to 1.8) | 1.1 to 1.5 |
| 2 Replayed_State and replay paths (2.1 to 2.7) | 2.1 to 2.9 |
| 3 Snapshot writer (3.1 to 3.2) | 3.1, 3.4, 3.5 |
| 4 Replay runner | 3.2 |
| 5 Backend (5.1 to 5.7) | 4.1 to 4.7 |
| 6 Studio (6.1 to 6.18) | 5.1 to 5.11 |
| 7 Testing strategy (7.1 to 7.7) | 1.4, 1.5, 2.7, 2.10, 3.1, 3.2, 4.3, 4.5, 4.6, 5.3, 5.4, 5.5, 5.6, 5.7, 5.10, 5.11, 5.12 |
| 8 Demo CLI and snippet module | 2.1, 2.6, 2.8, 3.3 |
| 9 Choices (C1 to C25) | Applied in the tasks named above; C18 (`.gitignore` entry for `tests/.sim.lock`) is applied in task 3.2 |
| 10 Open items (O1 to O5) | 2.10 (O5), 3.4 (O2, timing observed again), 3.3 (O3), 2.6 (O4) |

## Open items for the implementer

- Tier 2 and Tier 3 placeholders: the request asked for "reserved Tier 2/3 placeholders". Design 6.14 defines only the waveform slot, and no Tier 2 or Tier 3 appears in the design or the requirements. Only the waveform slot is built. Define the tiers in a design change before building more placeholders.
- The `tests/bus_driver.py` path in the request does not exist. The task uses `engine/bus_driver.py`, as design 2.4 states.
- `engine/demo.py` imports cocotb through `engine/bus_driver.py`. Task 3.3 checks this before the CLI depends on it.
- Design 7.4 has no dedicated test for `web/lib/sources.ts`. Task 5.8 covers it only through the manual smoke check in task 5.12.
- The 60-second budget (design O2) was measured on this repository, as reported. Task 3.4 re-runs the demo CLI, so the timing is observed again on the implementer's machine.

