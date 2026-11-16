# Kiro usage log

Every prompt given to Kiro for this project is recorded here, with the date and the result.

## 2026-11-15

Created the steering files regspectre.md and mmio_rules.md.

## Earlier work, reconstructed from git history

These entries are summaries of the prompts, not verbatim text. The commit hash is the evidence. Exact dates are in git log.

Requirements for the uart_core spec were written by the Kiro Spec agent and revised twice. Commits 5b34acc (requirements v2) and d0d9473 (requirements v3).

Design for the uart_core spec was written by the Kiro Spec agent and revised once. Commits 0a74cef (design v1) and 4a6c044 (design v2).

Tasks list with 10 tasks was written by the Kiro Spec agent. Commit 1304d9e (tasks v1).

Task 1, Kiro wrote rtl/uart_ctrl.sv and it compiled. Commit 54f33ef.

Task 1, Kiro wrote the cocotb tests in tests/test_uart_ctrl.py. Commit c2a9c88.

Task 1d, Kiro added overrun and same cycle tests, 11 cocotb tests passing in total. Commit 33490c6.

## 2026-11-15, Task 2

Prompt summary, run task 2 of tasks.md only, create engine/regmap.py and tests/test_engine_unit.py with regmap tests, no BOM, LF line endings, stop after the step.

Result. Kiro wrote conftest.py and tests/test_engine_unit.py, but engine/regmap.py was empty (0 bytes) and Kiro stopped with an upgrade message, so its free usage limit was most likely reached. The cause is not confirmed. The regmap.py code that Kiro had shown in its own command was written into the file from the Ubuntu terminal, and checked against the register map in design.md. 13 regmap tests pass. Commit e702d88.

## 2026-11-16, Task 3 part A

Prompt summary, run task 3 of tasks.md part A only, create engine/bus_driver.py with a BusDriver class (write, read, rmw, cycle stamps), no tests, no Makefile change, no BOM, LF line endings, stop after the step.

Result. Kiro read rtl/uart_ctrl.sv and tests/test_uart_ctrl.py first, then wrote engine/bus_driver.py (3234 bytes, no BOM, no CRLF, syntax checked with python3 -m ast). The code has not been run against the RTL yet, that happens in part B with the cocotb tests. Kiro wrongly said task 2 was unverified, but task 2 was verified by hand (13 tests pass, commit e702d88). Credits used for this run, 1.65 (credits arrived from the Devpost form). Commit cdb6b9e.

## 2026-11-16, Task 3 part B1

Prompt summary, run task 3 of tasks.md part B1 only, edit only engine/bus_driver.py, add an optional seed argument with seeded hw_set stimulus (each bit set with probability 1 in 8), a hw_log of (cycle, value), reset clearing hw_log, and an idle(n) method, no tests, no Makefile change, no BOM, LF line endings, stop after the step.

Result. Kiro rewrote engine/bus_driver.py (4914 bytes, no BOM, no CRLF, syntax checked with python3 -m ast, file read back to verify). The hw_set width of 4 bits was checked by hand against rtl/uart_ctrl.sv. The code has not been run against the RTL yet. Kiro raised one open point, reset does not reseed the random generator, so a second reset on the same driver continues the sequence. This will be fixed in a small follow up prompt. Credits used for this run, 1.46. Commit 66e16ca.

## 2026-11-16, Task 3 part B1 follow up

Prompt summary, small follow up on engine/bus_driver.py only, store the seed and reseed the random generator inside reset so every reset restarts the same hw_set sequence, update docstrings, no other behavior change, no BOM, LF line endings, stop after the step.

Result. Kiro applied four exact string replacements (each had to match once), file is now 5261 bytes, no BOM, no CRLF, syntax checked with python3 -m ast. Not yet run against the RTL, that happens in part B2. Credits used for this run, 1.24.

## 2026-11-16, Task 3 part B2a

Prompt summary, run task 3 of tasks.md part B2a only, add the PYTHONPATH export and test_bus_driver module to tests/Makefile, create tests/test_bus_driver.py with two tests (read plus W1C write, and cycle stamps for write, read, rmw and idle), Kiro must not run make, no BOM, LF line endings, stop after the step.

Result. Kiro edited tests/Makefile with exact string replacements and wrote tests/test_bus_driver.py (1780 bytes, no BOM, no CRLF, syntax checked). The simulation was run by hand in the Ubuntu terminal with cd tests and make, and all 13 cocotb tests pass (11 test_uart_ctrl and 2 test_bus_driver). This is the first run of bus_driver.py against the RTL. Seeded hw_set determinism, the rmw bug scenario and RDR read to clear are not tested yet, they come in part B2b. Credits used for this run, 0.75.

## 2026-11-16, Task 3 part B2b

Prompt summary, run task 3 of tasks.md part B2b only, edit only tests/test_bus_driver.py, keep the two existing tests, add four tests (rmw SET wipes the neighbor bit, direct write keeps the neighbor bit, RDR read to clear through the driver with rx_valid and rx_data driven from dut, seed determinism with reset reseeding), Kiro must not run make, no BOM, LF line endings, stop after the step.

Result. Kiro appended four tests (file is now 4907 bytes, no BOM, no CRLF, syntax checked). The simulation was run by hand in the Ubuntu terminal with cd tests and make, and all 17 cocotb tests pass (11 test_uart_ctrl and 6 test_bus_driver). The rmw test shows the hero bug on the real RTL, ISR |= bit 0 also clears the pending bit 3. Task 3 is complete. Credits used for this run, 0.66.

## 2026-11-16, Task 4 C subset parser

Prompt summary, run task 4 of tasks.md only, read the parser section of design.md and regmap.py, create engine/c_parser.py (Operation dataclass, ParseError, parse function in plain Python, no new package) and add parser unit tests to tests/test_engine_unit.py, Kiro must not run pytest, no BOM, LF line endings, stop after the step.

Result. Kiro wrote engine/c_parser.py (12195 bytes) and 24 parser tests next to the 13 regmap tests. Kiro followed the design and added the handler field to Operation and a SymbolError subclass of ParseError. Kiro only ran syntax checks, so a real bug was missed. The tokenizer produced lowercase token kinds (num, id, op) while the parser compared against uppercase (NUM, ID, OP), so 15 of 37 tests failed when run by hand with pytest, and the failing ones were exactly the tests that expect valid snippets to parse. Credits used for this run, 6.26. The 46 minute run time was mostly waiting for popup approval.

## 2026-11-16, Task 4 fix

Prompt summary, fix the token kind case in _tokenize only (m.lastgroup.upper()), then run pytest tests/test_engine_unit.py once and report the counts.

Result. One line changed in engine/c_parser.py. 37 of 37 tests pass (13 regmap and 24 parser). Checked again by hand, 37 pytest pass, 17 of 17 cocotb pass (uart_ctrl and bus_driver) and 1 of 1 smoke pass. Lesson, run make clean when switching TARGET, otherwise a stale sim_build runs the wrong toplevel. Credits used for the fix, 1.81.

## 2026-11-16, Task 5 intended state model

Prompt summary, run task 5 of tasks.md only, read the intended state section of design.md, regmap.py and the Operation dataclass, create engine/intended_model.py with intended_state(op, pre) (bits outside the named mask keep pre, W1C bits inside the mask follow write semantics, handle WRITE, RMW SET, RMW CLR and READ), add intended model unit tests to tests/test_engine_unit.py, Kiro runs pytest once and reports the counts, no BOM, LF line endings, stop after the step.

Result. Kiro wrote engine/intended_model.py (2056 bytes) and 13 intended tests next to the 37 existing tests. Kiro's first write was cut off after the import line, Kiro noticed that the tests were missing, appended them again and ran pytest once. 50 of 50 pass, checked again by hand, 50 pytest, 17 of 17 cocotb and 1 of 1 smoke. The design does not define the rule for READ operations, so Kiro chose that a read of UART_RDR clears its read to clear bits in the intended state, otherwise every single RDR read would look like a violation. The hero bug case is covered, pre 0b1001 with UART_ISR |= bit 0 gives intended 0b1000 while the real RTL gives 0b0000. Credits used for this run, 3.33.

## Task 6 part A, detector.py (summary)
Prompt summary: create engine/detector.py with Violation_Report and a function that reports every bit intended 1 and actual 0 on a UART_ISR read modify write, add 10 detector tests, run pytest once.
Result: engine/detector.py created and 10 detector tests added, Kiro reported 60 passed.
Problems seen: the first write of detector.py put a copy of the test file into it, the next two writes left it empty, and the fourth attempt with try and catch worked. Cause not confirmed. The test file hash still matched the 50 test version after those attempts.
Verified by hand in Ubuntu, pytest 60 passed, cocotb TESTS=17 PASS=17, smoke TESTS=1 PASS=1, git status showed only detector.py and test_engine_unit.py.
Open issue found in review, detector also reports bit 1 (RX_READY, read only) which could be a false positive. To be fixed before part B.
Credits used, about 5.23 for this run. Code commit 4515626.

## Task 6 part A fix, detector reports only W1C bits (summary)
Prompt summary: change engine/detector.py so only W1C bits of UART_ISR (taken from engine/regmap.py bit types, not hard coded) can produce a Violation_Report, so RX_READY bit 1 is never reported. Update the old bit 1 test, add 4 new detector tests (pre 0b0010 gives none, pre 0b1011 gives bit 3 only, actual wider than 4 bits raises ValueError, negative cycle raises ValueError), run pytest once.
Reason: found in my review of the first detector, the prompt said every bit and that would have given a possible false positive on a read only bit. The wording mistake was in my prompt, not in Kiro.
Result: Kiro reported 64 passed. All writes landed on the first try this time and sizes on disk were not zero.
Verified by hand in Ubuntu, pytest 64 passed, cocotb TESTS=17 PASS=17, smoke TESTS=1 PASS=1, git status showed only detector.py and test_engine_unit.py.
Not yet proven, the detector has only seen hand written actual values, not values from the real RTL. That comes in Task 8.
Credits used, about 2.94 for this run. Code commit 36afa9b.
