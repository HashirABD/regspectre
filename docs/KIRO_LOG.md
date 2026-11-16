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
