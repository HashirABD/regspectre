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
