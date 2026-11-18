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

## Task 6 part B, RDR double read detection (summary)
Prompt summary: add RDR double read detection per bit to engine/detector.py, reusing Violation_Report, keep detect_violations unchanged, a single read gives no report, add RDR detector tests, run pytest once. Kiro was told to pick the simplest reading if the design left the input format unclear and to say which rule it chose.
Result: Kiro added detect_rdr_double_reads(reads) taking a list of (op, value, cycle) tuples in program order, grouped by op.handler. The second UART_RDR read in a handler is compared with the first, and each read to clear bit that was 1 in the first value and 0 in the second is reported. Reads outside a handler are ignored and a third read is not compared. 11 new detector rdr tests added. Kiro reported 75 passed. All writes landed on the first try.
Choices made by Kiro, not defined by the design, the input tuple format, grouping by handler name only, and ignoring reads after the second. Kiro read design.md only with grep, so exact match with the design text is not confirmed by me.
Known gap, two separate invocations of the same handler name would be grouped together and could give a false positive. To keep in mind for Task 8.
Verified by hand in Ubuntu, pytest 75 passed, cocotb TESTS=17 PASS=17, smoke TESTS=1 PASS=1, git status showed only detector.py and test_engine_unit.py.
Not yet proven, the detector has not seen reads from the real RTL. That comes in Task 8.
Credits used, about 3.33 for this run. Code commit de77dfc.

## Task 7, engine/report.py JSON writer (summary)
Prompt summary: create engine/report.py that turns a list of Violation_Report objects into the JSON format from design.md, deterministic output, standard library only, add report tests, run pytest once. Kiro was told to pick the simplest reading where the design is unclear and to say which rule it chose.
Result: Kiro added report_to_dict and reports_to_json. Top level is a JSON array of violation objects with no wrapper and no summary count. Key order is register, bit, intended, actual, cycle, c_line. Violations keep input order. c_line is omitted when None, never written as null. Output uses indent 2 and no trailing newline. Wrong types raise TypeError (bool is rejected), out of range values raise ValueError. 12 new report tests added. Kiro reported 87 passed. All writes landed on the first try.
Choices made by Kiro, not defined by the design, the top level array with no wrapper, no summary count, input order, and the omitted c_line. Kiro read the JSON schema block of design.md (lines 259 to 287) in full, but I have not checked the exact match myself.
Verified by hand in Ubuntu, pytest 87 passed, cocotb TESTS=17 PASS=17, smoke TESTS=1 PASS=1, git status showed only report.py and test_engine_unit.py.
Not yet proven, the report has not seen violations from the real RTL. The UI spec depends on this format, so it must be final before the UI spec is written.
Credits used, about 3.58 for this run. Code commit d3fdb18.

## Task 8 part A, engine/demo.py ISR hero bug on real RTL (summary)
Prompt summary: create engine/demo.py with an async run_c_source(dut, source, seed) that parses a C snippet, replays the operations on the real RTL through BusDriver, reads pre and actual UART_ISR values, calls detect_violations and returns the reports plus JSON. Two ISR snippets (|= and direct assignment), tests/test_demo.py with 3 cocotb tests, test_demo added to the Makefile module list. Kiro was told not to run make or cocotb and only to run ast syntax checks.
Result: Kiro wrote demo.py, test_demo.py and changed one Makefile line. It made no pass claim, all expected values were derived by hand. Writes landed on the first try, sizes were not zero.
Choices made by Kiro, the seed drives only a background hw_set prefix that is followed by a reset, the replay itself has no seeded noise. The pre state 0b1001 is set with one hw_set pulse and bus.idle(1). Pre for a WRITE is a read before the write, actual is a read after each operation. A UART_RDR operation raises ValueError in part A.
Verified by hand in Ubuntu, pytest 87 passed, cocotb TESTS=20 PASS=20 (17 old plus 3 new), smoke TESTS=1 PASS=1, git status showed only Makefile, demo.py and test_demo.py. This proves on the real RTL that the |= snippet gives exactly one violation (UART_ISR bit 3, c_line 2, cycle 3) and the direct assignment gives an empty report.
Weak point, the seed has no effect on the replay, so the same seed test only shows that two runs without random noise are identical. It is not a strong determinism proof. To be decided before part 8B. The docstring of test_demo.py has odd wording (randomized-free) to fix later.
Not done yet, RDR double read replay, no LLM check, and the demo entry that prints the JSON. Task 8 is not complete.
Credits used, about 2.48 for this run. Code commit ec15868.

## Task 8 part 8B1: seeded replay in engine/demo.py (summary)
Prompt summary: rewrite run_c_source so the whole replay uses BusDriver with the seed, remove the old prefix that was followed by a reset, add optional trace dict, rewrite tests/test_demo.py (this is a summary, not the verbatim prompt).
Result: run_c_source(dut, source, seed, trace=None) now keeps the seeded hw_set noise active for the whole replay. seed None gives a quiet run. Kiro chose the timing rule, pre is read before the write, cycle is the commit edge, actual is read after the commit edge. tests/test_demo.py now has 7 cocotb tests.
Verified by hand: pytest 87 passed, cocotb TESTS=24 PASS=24, smoke TESTS=1 PASS=1, git status showed only engine/demo.py and tests/test_demo.py.
Review warnings: helper assumes first pre is 0b1001 for every seed (passed for seeds 7, 11, 13, 17, 19 only), pulse before noise is Kiro's hand reasoning, bit 1 noise is drawn but ignored by the RTL, _sampled_at needs a hw_log entry for cycle minus 1.
Known limit: when hardware sets bit 3 on the commit edge the detector reports nothing (about 1 seed in 8). Demo video must use the quiet run (seed None) and the write up must state this limit.
Credits used: about 4.91 (Kiro estimate).
Commit: 0efd7bb

## Task 8 part 8B2: RDR double read replay in engine/demo.py (summary)
Prompt summary: add RDR_DOUBLE_READ_SNIPPET and RDR_SINGLE_READ_SNIPPET and an async run_c_rdr_source that replays UART_RDR reads through BusDriver on the real RTL, builds (op, value, cycle) tuples and calls detect_rdr_double_reads, plus new cocotb tests in tests/test_demo.py (this is a summary, not the verbatim prompt).
Result: run_c_rdr_source(dut, source, seed=None, trace=None) returns (reports, json_text). Kiro chose rx_data 0xA5 driven with rx_valid high for one edge after reset, value taken before the commit edge, cycle is the commit edge. tests/test_demo.py now has 12 cocotb tests (7 old plus 5 new).
Verified by hand: pytest 87 passed, cocotb TESTS=29 PASS=29, smoke TESTS=1 PASS=1, git status showed only engine/demo.py and tests/test_demo.py. The double read gives bits 0, 2, 5, 7 with cycle 3 and c_line 3, the single read and two different handlers give an empty report, same seed gives identical JSON and hw_log, and five seeds (7, 11, 13, 17, 19) gave the same RDR reports.
Known gaps: grouping is by handler name, so two invocations of the same handler name would be one group and could give a false positive (no test yet). Only one rx_data value (0xA5) was tested. The seed independence is shown for five seeds only, not proven for all.
Credits used: about 4.82 (Kiro estimate).
Commit: 46d5a96

## Task 8 part 8B3: format_report, demo entry, determinism test, static no LLM check (summary)
Prompt summary: add format_report and a main() usage entry to engine/demo.py, add one three run determinism cocotb test to tests/test_demo.py, and add a new pure Python tests/test_no_llm.py that scans engine/ with ast (this is a summary, not the verbatim prompt).
Result: format_report(json_text) returns the text plus one final newline and raises TypeError for non strings. python3 -m engine.demo only prints a usage message, it does not run cocotb or iverilog. tests/test_demo.py now has 13 cocotb tests. tests/test_no_llm.py has 6 tests, 3 of them are negative or allow list tests for the scanner.
Differences from tasks.md (decided by me, Kiro followed my step and reported them): tasks.md wanted the determinism and no LLM checks in test_engine_unit.py (-k determinism, -k no_llm) and python -m engine.demo printing reports. I used a new file for no LLM, a seed None three run test in test_demo.py, and a usage message entry. This is an open decision for Task 10.
Verified by hand: pytest engine 87 passed, pytest no_llm 6 passed, cocotb TESTS=30 PASS=30, smoke TESTS=1 PASS=1, git status showed only engine/demo.py, tests/test_demo.py and the new tests/test_no_llm.py.
Not verified: python3 -m engine.demo has not been run by hand yet (cocotb import outside the simulator is unconfirmed).
Limits: the no LLM check is static. It finds forbidden imports from a closed list and direct eval or exec calls. It does not catch __import__, importlib, subprocess or SDKs outside the list, so it is not proof that no network is used at run time. Determinism was shown for seed None over three runs only.
Credits used: about 6.86 (Kiro estimate).
Commit: 8f234ca

## Task 9 part A, Hypothesis property tests 1 to 7

Prompt summary (this is a summary, not the verbatim prompt): asked Kiro to read design.md Properties 1 to 7 and the existing engine files, then write tests/test_engine_props.py with one Hypothesis test per property, without touching engine files, design.md, requirements.md, tasks.md or rtl/uart_ctrl.sv.

Result: 7 Hypothesis tests for Properties 1 to 7 in tests/test_engine_props.py. Kiro added derandomize=True on its own. Bit 1 follows Requirement 1.8 and the intended model. The actual value in the tests comes from a test side W1C model, not from the RTL.

Verified by hand in the Ubuntu terminal: pytest engine 87 passed, no_llm 6 passed, props 7 passed, cocotb 30 of 30, smoke 1 of 1, git status showed only the new file.

Known weak points: derandomize=True means the same 100 examples run every time. Properties 3, 4 and 5 check engine logic against a test side model, not against real hardware (only Property 8 will do that). The example count for all 7 tests is not confirmed. The design.md Property 2 wording conflicts with Requirement 1.8 and is still open.

Credits used: about 5.43
Commit: 5fc3110

## Design fix, Property 2 wording in design.md

Prompt summary (this is a summary, not the verbatim prompt): asked Kiro to read Requirement 1 (criteria 1.7 and 1.8), the Property 2 section of design.md and the Property 2 test in tests/test_engine_props.py, then fix only the Property 2 wording so it agrees with Requirement 1.8, changing as little as possible and touching no other file.

Result: Kiro changed one line in design.md. The W1C write effect formula now applies only to bits inside M of type W1C, and a new sentence says that a non W1C bit inside M keeps its pre value, with bit 1 (RX_READY, read only) as the example, per Requirement 1.8. design.md kept its existing UTF-8 BOM and LF line endings (no CRLF).

Verified by hand in the Ubuntu terminal: git status showed only design.md, git diff stat showed 1 insertion and 1 deletion, the diff with cat -A showed no CRLF, and the full new line was read on screen and ends with Requirement 1.8. No tests were run, because this was a text only change.

Known weak points: Kiro's claim that Requirement 1.7 is not relevant to Property 2 was not checked by me line by line. The new wording says "not W1C" in general, but only bit 1 of UART_ISR is a non W1C bit in the ISR mask case. How RDR (RTC) bits fit under Property 2 is not confirmed.

Credits used: about 5.4 (Kiro's own estimate)
Commit: 0c9fbbf

## Task 9 part B1, Property 8 RTL timing test

Prompt summary (this is a summary, not the verbatim prompt): asked Kiro to read design.md Property 8, Requirement 9, Task 9 and the bus driver, then write only tests/test_pbt_hw_timing.py. A cocotb test where Hypothesis draws a per cycle hw_set schedule, a write cycle and a target BIT, issues UART_ISR = (1U << BIT) on the real RTL, and fails with a neighbor wipeout message if another W1C bit goes from set to cleared. Kiro must not run make or cocotb, and must not touch the Makefile or engine files.

Result: one cocotb test. Kiro found that Hypothesis rejects async tests, so the @given test runs in a worker thread and sends each case over a queue to the cocotb side, which runs it on the RTL. W1C bits come from regmap bit_type, hw_set bit 1 is never driven, and the pre value is sampled at the falling edge before the commit. Kiro added suppress_health_check too_slow on its own. File is 6771 bytes, no BOM, no CRLF.

Verified by hand in the Ubuntu terminal: bit_type for UART_ISR gives W1C, RO, W1C, W1C. Running make with COCOTB_TEST_MODULES=test_pbt_hw_timing gave TESTS=1 PASS=1 FAIL=0, the test printed 100 examples ran and passed, and the run took about 3.6 seconds. git status showed only the new file. The Makefile module list is not updated yet (Task 9 part B2).

Known weak points: the test has no negative control, so it is not shown that it can catch a wipeout (an RMW style write should be tried against it). The printed count includes replays, so it does not prove 100 distinct examples. The shrinking path never ran because nothing failed. Schedule entries after the write are shifted one edge later. The pass shows only that this RTL did not wipe a neighbor on direct assignment in this run. It is randomized testing, not proof, and it does not check the RMW model used in Properties 3 to 5.

Credits used: about 6.95 (Kiro's own estimate)
Commit: 44237e6

## Task 9 part B2: add test_pbt_hw_timing to the uart_ctrl cocotb module list
- Prompt summary (summary, not verbatim): change exactly one line in tests/Makefile, the uart_ctrl COCOTB_TEST_MODULES line, to add test_pbt_hw_timing. No BOM, LF only, keep missing trailing newline, do not run make or cocotb, do not start Task 10.
- Result: Kiro changed only that line. Kiro reported size 510 to 529 bytes (19 bytes for ",test_pbt_hw_timing"), BOM False, CRLF False, no trailing newline kept.
- Verified by hand: git diff showed 1 file, 1 insertion, 1 deletion, only the module line changed. Full check in Ubuntu: pytest engine 87 passed, no_llm 6 passed, props 7 passed, cocotb TESTS=31 PASS=31 FAIL=0, pbt printed "100 examples ran and passed", smoke TESTS=1 PASS=1, git status showed only tests/Makefile modified.
- Not proven by this step: Property 8 has no negative control yet, so it is not shown that the test can catch a neighbor wipeout. The printed count includes Hypothesis replays.
- Credits used: 4.65 (Kiro estimate)
- Commit: 0453c76

## Task 9 parts C1 and C1b, negative control for Property 8
Prompt summary (a summary, not the verbatim prompt). C1 asked Kiro to create tests/test_pbt_negative_control.py, one cocotb test that runs the |= hero bug as an RMW on the real RTL (pre 0b1001, ISR |= bit 0) and checks that the wipeout condition reports bit 3. C1b asked for fixes, removing the meaningless final assert, asserting pre in every seeded case, and a comment that the wipeout function is a copy.
Result. C1 file created by Kiro (3910 bytes, ast check only, not run by Kiro). C1b rewrote it (6208 bytes, no BOM, no CRLF). Three of the seven checks I requested in C1b were wrong (post bit 0 always 0, post only 0b0000 or 0b1000, bit 0 check). Kiro refused them and instead asserted that post bit 0 and bit 3 equal the hw_set bits sampled at the commit edge from hw_log. Kiro also added a helper _run_hero_rmw that I did not ask for.
Verified by hand. Ran the test alone in the Ubuntu terminal, TESTS=1 PASS=1 FAIL=0. Quiet case pre=0b1001 post=0b0000 wiped=[3]. Seeds 7 and 17 gave post 0b1000 (hardware set wins, Requirement 1.7, now confirmed by the hw_log asserts), seeds 11, 13, 19 gave post 0b0000. Wipeout detected in 4 of 6 cases.
Not proven. This control shows only that the wipeout condition flags a known bad RMW result on the real RTL. It does not show that the real Property 8 pipeline (worker thread, queue, falling edge pre sample) fails on a bad write. The wipeout function is a copy and can drift from tests/test_pbt_hw_timing.py. Only 5 seeds were run, so the rate of missed reports is not confirmed. The test is not yet in the Makefile.
Credits. C1 5.14, C1b 5.13.
Commit. 8ed29b2 (pushed).

## Task 9 part C2, negative control added to the uart_ctrl cocotb module list
Prompt summary (a summary, not the verbatim prompt). Kiro was asked to change one line in tests/Makefile, adding test_pbt_negative_control at the end of the uart_ctrl COCOTB_TEST_MODULES line, with no BOM, LF, no trailing newline, size 529 to 555 bytes, and not to run make or cocotb. A first draft of this prompt had wrong byte numbers, I corrected it before sending, only the corrected prompt went to Kiro.
Result. Kiro changed only line 14, size 529 to 555 (26 bytes), no BOM, no CRLF, last byte unchanged. Kiro checked the old line matched once before writing.
Verified by hand. git diff showed 1 file, 1 insertion, 1 deletion, only line 14. Full check in the Ubuntu terminal, pytest 87, 6, 7 passed, cocotb TESTS=32 PASS=32 FAIL=0, pbt printed 100 examples ran and passed, negative control printed 4 of 6 detected, smoke 1 of 1. Recently changed files showed nothing unexpected.
Not proven. Property 8 real pipeline (worker thread, queue, falling edge pre sample) still has no negative control. The printed 100 examples includes Hypothesis replays.
Credits. C2 4.89.
Commit. 57800ac (pushed).

## Task 9 part D1, Property 8 pipeline moved into a function with a write method parameter
Prompt summary (a summary, not the verbatim prompt). Kiro was asked to refactor only tests/test_pbt_hw_timing.py with no behavior change. The pipeline (worker thread, queue, falling edge pre sample, post read) moves into run_wipeout_check(dut, bus, write_method). The real test passes direct_write. Same rule, same max_examples=100, no derandomize, _wiped_neighbours kept. No BOM, LF, Kiro not allowed to run make or cocotb.
Result. Kiro wrote the file, 7600 bytes, no BOM, no CRLF, python3 -m ast syntax check passed. Kiro also edited the module docstring, because the old line saying the Makefile does not list the module was out of date. Kiro raised a caveat for D2, bus.rmw reads first, so its commit comes two edges after the falling edge pre sample, and the pre value may differ from the old value that rmw returns.
Verified by hand. Full check in the Ubuntu terminal, pytest 87, 6, 7 passed, cocotb TESTS=32 PASS=32 FAIL=0, pbt printed 100 examples ran and passed, negative control printed 4 of 6 detected, smoke 1 of 1. git status showed only tests/test_pbt_hw_timing.py modified. I read the full git diff by hand, 38 insertions and 20 deletions, bus calls and their order unchanged.
Not proven. The pipeline has still never been shown to fail on a bad write, that is D2. The RMW pre value question is open, cause and effect not confirmed. The printed 100 examples includes Hypothesis replays.
Credits. D1 5.38.
Commit. a1ca0be (pushed).

## Task 9 part D2, negative control for the Property 8 pipeline with an RMW write
Prompt summary (a summary, not the verbatim prompt). Kiro was asked to create only tests/test_pbt_pipeline_negative_control.py. One cocotb test runs run_wipeout_check with an RMW write method (bus.rmw with SET, the |= hero bug) and expects an AssertionError containing "neighbor wipeout". Kiro was told to keep the pre sample at the falling edge before the write, to read the RTL to check that a set W1C bit only clears by a software write, and not to run make or cocotb.
Result. Kiro wrote the file, 2994 bytes, no BOM, no CRLF, python3 -m ast syntax check passed. Kiro reported from reading the RTL that W1C bits 0, 2 and 3 clear only by a bus write to UART_ISR or by reset, and that the rmw write commits two rising edges after the pre sample.
Verified by hand. I ran the file alone in the Ubuntu terminal with make COCOTB_TEST_MODULES=test_pbt_pipeline_negative_control, TESTS=1 PASS=1 FAIL=0. Output, neighbor wipeout schedule=[1, 0] BIT=2 write_at=1 commit_cycle=3 pre=0b0001 post=0b0000 cleared=[0], exception type AssertionError. I checked this counterexample by hand against the RTL logic. git status showed only the new untracked file.
Proven. The Property 8 pipeline (worker thread, queue, falling edge pre sample, post read) detects at least one bad RMW write, the Hypothesis shrinking path ran through the bridge, the sibling import works under cocotb.
Not proven. One run only, not repeated. The test is not in tests/Makefile yet, that is D3. The HypothesisSideeffectWarning messages in the output have a cause that is not confirmed. A negative control shows that the pipeline can fail, it does not show that the real test never fails wrongly.
Credits. D2 5.77.
Commit. 7370a94 (pushed).

## Task 9 part D3, add pipeline negative control to Makefile
Prompt summary (a summary, not the verbatim prompt). Add test_pbt_pipeline_negative_control at the end of the uart_ctrl COCOTB_TEST_MODULES line in tests/Makefile, nothing else, check the old line matches once, write without BOM and with LF, do not run make or cocotb.
Result. Kiro changed line 14 only. Size 555 to 590 bytes, no BOM, no CRLF, no trailing newline. Kiro's report wrote "line 555" for the old line match, which was a wrong wording for the byte size, harmless.
Verified by hand. git diff showed 1 insertion and 1 deletion in tests/Makefile only. wc gave 590 bytes, file says ASCII text. Full check passed, pytest 87, 6, 7 passed, cocotb TESTS=33 PASS=33, pbt 100 examples ran and passed, negative control detected in 4 of 6 cases, pipeline negative control line printed with AssertionError, smoke TESTS=1 PASS=1. git status and recently changed files showed only tests/Makefile.
Not proven. The suite ran once, the .hypothesis cache can replay old examples. The pipeline negative control shows the pipeline can fail, not that the real Property 8 test never fails wrongly. The cause of the HypothesisSideeffectWarning lines is not confirmed, the grep did not show them in this run.
Credits. 5.25.
Commit. 5b5852c.

## Task 9 part E, negative control imports the shared wipeout function
Prompt summary (a summary, not the verbatim prompt). Compare _wiped_neighbours in tests/test_pbt_hw_timing.py with the copy in tests/test_pbt_negative_control.py, and if equivalent replace the copy with a by name import, keep every printed line, assertion and value, do not run make or cocotb.
Result. Kiro reported the two functions equivalent and changed only tests/test_pbt_negative_control.py. The copied function, W1C_BITS and the bit_type import were removed, and the line from test_pbt_hw_timing import _wiped_neighbours was added. Size 6208 to 5841 bytes, no BOM, no CRLF, python3 -m ast passed. Kiro read design.md Property 8 only by grep, not by reading the section, which was against the prompt. No effect on this step, noted anyway.
Verified by hand. git diff showed 4 insertions and 12 deletions in that one file. The removed function body matched line 59 of test_pbt_hw_timing.py word for word. grep showed no W1C_BITS or bit_type left in the negative control. Full check passed, pytest 87, 6, 7 passed, cocotb TESTS=33 PASS=33, negative control output identical (quiet wiped [3], seeds 7 and 17 wiped [], detected in 4 of 6 cases), pipeline negative control line printed, smoke TESTS=1 PASS=1.
Not proven. One run only, the .hypothesis cache can replay old examples. The negative control was not broken on purpose after this change, so it is not shown that a wrong _wiped_neighbours would make it fail. Correction to the D3 entry. It said the grep did not show the HypothesisSideeffectWarning lines, but that grep does not filter for them, so this says nothing about whether they appeared. Their cause is still not confirmed.
Credits. 5.51.
Commit. d019328.

## Task 10 part A, tasks.md text fix (17 November 2026)
- Prompt summary (a summary, not verbatim): Kiro was asked to fix four stale or wrong passages in .kiro/specs/uart_core/tasks.md only (Task 8 determinism and no LLM placement, Task 8 Verify line, Task 9 Verify line, Task 10 module list and counts).
- Result: four passages changed, 4 insertions and 4 deletions, tasks.md is 13483 bytes, no BOM, no CR. Commit 2ef199c.
- Verified by hand: git diff stat shows only tasks.md. Both test names Kiro wrote exist (test_seed_determinism at tests/test_bus_driver.py line 118, test_demo_isr_rmw_three_quiet_runs_are_byte_identical at tests/test_demo.py line 331). Full check after the edit: pytest 87, 6, 7 passed, cocotb TESTS=33 PASS=33, smoke TESTS=1 PASS=1.
- Facts found by hand before this edit: pytest tests/ gives 100 passed and collects only test_engine_unit.py (87), test_no_llm.py (6), test_engine_props.py (7), no cocotb file. Kiro called this probably wrong without running it, the collect only run showed it is right. Example counts from Hypothesis statistics are 100, 100, 100, 64, 32, 100, 100 (Properties 4 and 5 ended with nothing left to do). The Task 8 filter -k "determinism or no_llm" on test_engine_unit.py selects nothing (exit code 5), so the old Task 8 Verify line failed when run literally.
- Not proven: the phrase "check the JSON reports" for test_demo.py in Task 8 line 61 is Kiro's wording and was not checked against the test code. The k filters regmap, parser, intended, detector, report overlap (13, 24, 14, 26, 31 selected, total 108 against 87 tests) and intended selects 14 tests, cause not confirmed. Kiro said it re read tasks.md, the read tool reused an earlier read, so a fresh read in this run is not confirmed.
- Credits: 5.74 estimated by Kiro.

## Task 10 part B1, demo runner python3 -m engine.demo run (18 November 2026)
- Prompt summary (a summary, not verbatim): Kiro was asked to add a runner so that python3 -m engine.demo run replays four demo snippets (ISR_RMW, ISR_DIRECT, RDR_DOUBLE_READ, RDR_SINGLE_READ) on the real RTL through cocotb and prints each name, C source and report. No argument had to keep the usage message and exit 0. The default make had to stay at 33 tests and tests/test_no_llm.py must not be weakened.
- Result: engine/demo.py changed (11999 bytes), tests/demo_print.py created (1739 bytes, not collected by pytest because its name does not start with test_). The runner calls make with COCOTB_TEST_MODULES=demo_print in tests, the cocotb module writes a temporary JSON file, the parent validates and prints it. tests/Makefile unchanged (590 bytes). Commit d725efe.
- Verified by hand: git diff showed the removed lines are only the old USAGE text, old main and its call, format_report lines were not removed. No argument prints the new usage and exits 0. pytest tests/ 100 passed, cocotb TESTS=33 PASS=33, smoke TESTS=1 PASS=1. python3 -m engine.demo run exits 0 and prints four blocks: ISR_RMW one violation (UART_ISR bit 3, intended 1, actual 0, cycle 3, c_line 2), ISR_DIRECT [], RDR_DOUBLE_READ bits 0, 2, 5, 7 (cycle 3, c_line 3), RDR_SINGLE_READ []. These match the Task 8 numbers. Negative control with a wrong cocotb module name made run_demo return 1 with "make exited with status 2" on stderr. git status stayed clean apart from the two files.
- Not proven: only one failure path was tested (make failure). Missing output file, wrong snippet order and a report that is not a JSON array have no negative control. The runner does not judge whether a report is right, it only checks for a JSON array, correctness comes from tests/test_demo.py. python3 -m engine.demo run has no automated test, only the hand run. Kiro read design.md only by grep again, against the prompt. It did not run the runner itself, as instructed.
- Credits: 5.29 estimated by Kiro.

## studio_ui requirements.md draft (18 November 2026)
- Prompt summary (a summary, not verbatim): Kiro (Spec agent) was asked to write only .kiro/specs/studio_ui/requirements.md in EARS notation for the Next.js studio with a FastAPI backend, a recorded snapshot fallback, a 32 bit register array, a violation list built from the report JSON, a reserved waveform region, error cases and wording rules. No design.md, no tasks.md, no other file.
- Result: requirements.md, 27812 bytes, no BOM, no CR, 10 requirements, 119 numbered criteria. Commit e47701e. Kiro read design.md, report.py and demo.py in full this time. demo_print.py and the Makefile came back as cached reads from earlier in its session. Kiro ran an automatic detailing pass (ten detailer calls and one merge) although the prompt said to stop after requirements.md, only requirements.md changed.
- Verified by hand: size, no BOM, CR count 0, git status showed only the studio_ui folder, web folder holds only .gitkeep.
- Known issue found by hand: Requirement 9 criterion 1 says Requirement 8 criteria 7 and 11, but after detailing the intended rules are criteria 10 and 14 (7 is the snapshot writer rule, 11 is the label rule). Committed as a draft, fix comes in a new commit.
- Not proven: the other 118 criteria were not checked line by line by me. Whether engine/c_parser.py rejects writes to RX_READY is not confirmed, the grep found no RX_READY text in c_parser.py. The Snapshot writer and a new engine entry point for user typed C do not exist yet, the requirements need them. Requirement 7 criterion 9 says the simulation was stopped after 70 seconds without a response, the Studio cannot know that, unconfirmed claim. The report carries only violation bits, so most register cells will show no violation reported, a design decision is still open. Parser error versus busy order is not defined, Kiro chose parser first.
- Credits: 5.06 estimated by Kiro.

## studio_ui requirements fix A (18 November 2026)
- Prompt summary (a summary, not verbatim): Kiro was asked to edit only .kiro/specs/studio_ui/requirements.md with two exact string edits. Requirement 9 criterion 1 had to point to Requirement 8 criteria 10 and 14, and Requirement 7 criterion 9 had to show a message that does not claim the simulation was stopped. It also had to check every other cross reference.
- Result: two lines changed, 2 insertions and 2 deletions, file 27834 bytes, no BOM, no CR. Commit 8b33328. Kiro read the whole file, edited directly with no subagent chain, 1.66 credits estimated by Kiro.
- Verified by hand: git status showed only this file, git diff showed exactly the two intended lines, size 27834, first bytes "# R", CR count 0.
- Not proven: Kiro's table of 16 cross references was not checked by me line by line, only the two changed lines. The other 118 criteria are not checked line by line. Requirement 7 criterion 9 and Requirement 9 criterion 6 now show two different messages for a missing response, which may confuse users, to be reviewed in the design step. Kiro's PowerShell output was cut off again and it verified the file with a separate command.

## studio_ui requirements part B (18 November 2026)
- Prompt summary (a summary, not verbatim): Kiro was asked to edit only .kiro/specs/studio_ui/requirements.md with two user decisions. First, a strict parser as a NEW entry point that calls the existing parse function and adds three extra checks (write to RX_READY, no handler, both registers), with the existing parse left unchanged. Second, a separate Replayed_State output (pre and post of the selected register) next to the unchanged report array, with the RDR post value measured from the RTL.
- Result: requirements.md changed from 27834 to 30770 bytes, no BOM, no CR, 10 requirements, Requirement 3 now has 25 criteria. Commit 96d19ea. Kiro read the whole file and engine/demo.py lines 30 to 110 and 126 to 190, edited directly with no subagent, 3.95 credits estimated by Kiro.
- Facts found by hand before the edit: the existing parse accepts a write to RX_READY (mask 2), a snippet with no handler, and a snippet that uses both UART_ISR and UART_RDR. It rejects a write to UART_RDR and an if statement. run_c_source records pre and actual only for WRITE and RMW. run_c_rdr_source records the value before each read and no value after it.
- Verified by hand: git status showed only this file, size 30770, first bytes "# R", CR count 0, 10 requirement headings, 25 criteria in Requirement 3, no old references to criteria 2 to 5, 2 to 6 or criterion 21 left, the new entry point lines are on disk.
- Not proven: Kiro's table of cross references was not checked by me line by line. The meaning of the new and rewritten criteria was not checked line by line. The new entry point name and signature were not checked against engine/c_parser.py. Known open issues committed on purpose: the Snapshot keeps report as an embedded array while the backend returns report as a string, the state for a snippet with only ISR reads is not defined, parser versus busy order is undefined, and Requirement 7 criterion 9 and Requirement 9 criterion 6 show different messages. Kiro's PowerShell output came back cut off again and it verified the file with separate byte checks.

## studio_ui requirements fix C (18 November 2026)
- Prompt summary (a summary, not verbatim): Kiro was asked to edit only .kiro/specs/studio_ui/requirements.md so that the Snapshot report value is stored as a JSON string, the same form as the report in a Backend response, and to add one criterion that the Studio uses the same reader for both. Nothing else was to be decided.
- Result: requirements.md changed from 30770 to 31410 bytes, no BOM, no CR, 10 requirements, Requirement 8 now has 16 criteria. Commit 873a787. Kiro read the whole file in two parts, edited directly with no subagent, 2.03 credits estimated by Kiro. Kiro caught and fixed its own missing blank line before the Requirement 9 heading.
- Verified by hand: git status showed only this file, size 31410, first bytes "# R", CR count 0, 10 headings, 16 criteria in Requirement 8, blank line before the Requirement 9 heading, the only reference to Requirement 8 criteria is now "criteria 11 and 15" in Requirement 9 criterion 1, the word embedded no longer appears and JSON string appears in the Glossary, Requirement 6 criterion 7 and Requirement 8 criterion 5.
- Not proven: the meaning of the new and rewritten criteria was not checked line by line. Requirement 8 criterion 16 says a report that cannot be read under criterion 6, but criterion 6 does not define the reader, only says to use the same one. Kiro's own byte check came back cut off in the shell, my hand check confirmed it. Still open on purpose: state for a snippet with only ISR reads, parser versus busy order, the two different no response messages (Requirement 7 criterion 9 and Requirement 9 criterion 6), and the new entry point name against engine/c_parser.py.

## studio_ui requirements fix D (18 November 2026)
- Prompt summary (a summary, not verbatim): Kiro was asked to edit only .kiro/specs/studio_ui/requirements.md with four decisions. First, a run request that fails the new entry point or the size check gets its own response even while a simulation is running, so parser error beats busy. Second, a snippet with only UART_ISR reads has a null Replayed_State and the Studio shows not replayed. Third, one common text for the no response case in Requirement 7 and Requirement 9. Fourth, Requirement 8 criterion 16 points to Requirement 9 criterion 4 as the reader rule.
- Result: requirements.md changed from 31410 to 32491 bytes, no BOM, no CR, 10 requirements, Requirement 7 now has 10 criteria. Commit 70d106b. Kiro read the whole file in two parts, edited directly with no subagent, 2.39 credits estimated by Kiro. Kiro caught and fixed its own missing blank line before the Requirement 8 heading.
- Verified by hand: git status showed only this file, size 32491, first bytes "# R", CR count 0, 10 headings, 10 criteria in Requirement 7, blank lines before the Requirement 8 and 9 headings, Requirement 9 criteria 11 and 12 now cite Requirement 7 criteria 7 and 9, the text No response arrived appears in Requirement 7 criterion 10 and Requirement 9 criterion 6, the old text stopped responding is gone.
- Not proven: the meaning of the new criteria was not checked line by line. Known open issue committed on purpose: Requirement 9 criterion 6 shows a message that says within 70 seconds, but its trigger (no response after the status check succeeded) has no 70 second limit. This came from my prompt, I asked for one common message without checking that the triggers differ. Requirement 8 criterion 6 still says the same reader without naming Requirement 9 criterion 4. The order of invalid_request (400) against busy is not defined. Kiro's cross reference table was not checked by me line by line.

## studio_ui requirements fix E (18 November 2026)

Prompt summary (summary only, not verbatim): Kiro was asked to remove the duplicate no response criterion (Requirement 9 criterion 6, same situation as Requirement 7 criterion 10 but without the 70 second limit) and to make Requirement 8 criterion 6 name Requirement 9 criterion 4 as the reader rule.

Result: requirements.md went from 32491 to 32242 bytes. Commit 70e2dd9 (9 insertions, 10 deletions). Kiro credits 2.11 (Kiro's own estimate).

Verified by hand: no BOM (first bytes "# R"), CR count 0, 10 requirement headings, Requirement 9 has 13 criteria numbered without a gap, blank line before every requirement heading, "No response arrived" appears only in Requirement 7 criterion 10.

Not proven: Kiro compared 9.6 and 7.10 before deleting and said only the "status check succeeded" condition is lost and it changes no outcome. That is Kiro's claim, I did not verify it. The meaning of the new wording and Kiro's cross reference table were not checked line by line. Cause of nothing else is confirmed.

## Handoff checks, Steps 57 to 60 (18 November 2026, no Kiro run, read only checks)

Summary: I checked git log and commit 2ef199c by hand against the handoff text. No Kiro prompt was used and no repo file other than this log was changed.

Findings by hand. First, the handoff said uart_core tasks.md was NOT changed in Task 10. That was wrong. Commit 2ef199c (Task 10 A) changed 4 lines in .kiro/specs/uart_core/tasks.md (Task 8, 9 and 10 verify text). The studio_ui commit chain is e47701e, 8b33328, 96d19ea, 873a787, 70d106b, 70e2dd9, each followed by its log commit. Second, the handoff said the example count of the 7 engine properties was not confirmed. I ran pytest tests/test_engine_props.py with --hypothesis-show-statistics. Result: Properties 1, 2, 3, 6, 7 ran 100 passing examples (stopped by max_examples=100), Property 4 ran 64 and Property 5 ran 32 (stopped because nothing left to do), 0 failing and 0 invalid everywhere, 7 passed. This matches the tasks.md text.

My own mistake: my first command in Step 59 used a grep pattern that did not match the statistics text, so it showed no counts. Step 60 fixed it.

Not proven: this shows how many examples ran, not that the properties check the right thing. Why Property 4 has exactly 64 cases was not checked against its strategy. Hypothesis is randomized testing, not proof. The content of the 4 changed tasks.md lines was read in the diff but not compared line by line with the current code. Cause of nothing else is confirmed.

## Parser entry point checks, Steps 62 to 64 (18 November 2026, no Kiro run, read only checks)

Summary: I checked engine/c_parser.py and studio_ui requirements.md by hand for the name and error shape of the parser. No Kiro prompt was used and no repo file other than this log was changed.

Findings by hand. engine/c_parser.py has one public parse function, parse(snippet), plus ParseError, SymbolError (a subclass of ParseError) and Operation. requirements.md never names the new strict entry point, it only says "the new entry point", so the name and signature must be decided in design.md. ParseError has the attributes line and message (docstring says 1 based line). A hand run of parse on two bad snippets gave SymbolError with line 1 for 'UART_ISR |= (1U << NOPE);' and line 2 when a blank line comes first, message "unknown bit 'NOPE' for UART_ISR". So the HTTP 422 body fields line and message can come from e.line and e.message.

My own mistake: in Step 62 I said I suspected ParseError might have no line number. It does have one. The doubt was wrong and I should have read the class before raising it.

Not proven: only one error type (unknown bit) was tried. Other error paths, errors on later lines of a longer snippet, and whether line can ever be 0 or None were not tested. Operation.c_line is int or None, so whether the requirement 15 line number always exists is not decided. Cause of nothing else is confirmed.
