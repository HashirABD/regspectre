# Design Document

## Overview

studio_ui adds five parts to RegSpectre. Each part has one owner.

1. A strict parser entry point, `parse_user_snippet`, in `engine/c_parser.py`. The existing `parse` function does not change.
2. A `Replayed_State` value for every replay. It is measured from the uart_ctrl RTL during the run.
3. A Snapshot writer. `python3 -m engine.demo run` calls it after all four demo replays pass.
4. A local FastAPI Backend in `backend/`. It validates requests, runs one simulation at a time, and returns the report text and `replayed_state`.
5. A Next.js Studio in `web/`. It shows only what the Backend or the Snapshot returns. Every response is checked by one shared reader.

Scope: the uart_ctrl block only, the C subset only, Icarus Verilog through cocotb. The waveform view and the one-click auto fix are not designed here. Only their reserved places appear in the layout.

The engine stays deterministic Python. No component makes an LLM call. This spec implements the local 127.0.0.1 architecture that Requirement 6 requires. Docker and public cloud deployment are scheduled for a separate Deployment spec, after studio_ui works and is tested locally (D8).

## Decisions

| ID | Decision | Reason |
|---|---|---|
| D1 | The Backend lives in `backend/`, not in `engine/`. | `tests/test_no_llm.py` scans only `engine/`, so it passes unchanged. |
| D2 | One cocotb replay module, `tests/snippet_run.py`, serves both the demo CLI and the Backend. `tests/demo_print.py` is retired. | One replay path means the Snapshot and the Backend show the same results. |
| D3 | Request checks run in this order: too_large, invalid_request, parser_error, busy. All three checks run before any lock is taken. | The same invalid request gets the same answer whether a simulation is running or not. |
| D4 | The strict parser is `parse()` plus a per-line form matcher. It has no second tokenizer and no tree. | `parse()` tokenizes and computes values. The matcher only accepts exact statement lines. |
| D5 | The RDR post value is sampled with `BusDriver.peek`, which does not assert a read strobe. | A read clears UART_RDR. The probe must not clear it. |
| D6 | The simulation lock is a `threading.Lock` in the Backend plus `flock` on `tests/.sim.lock`. The CLI uses the same file lock. | The CLI and the Backend cannot both use `tests/sim_build` at once. |
| D7 | `engine/replayed_state.py`, `engine/snapshot.py`, `engine/sim_runner.py` and `engine/snippets.py` do not import cocotb. | The Backend and the unit tests can import them without a simulator. |
| D8 | `studio_ui` implements the local 127.0.0.1 architecture that Requirement 6 requires. Docker and public cloud deployment (a configurable bind host, configurable CORS origins, and a `BACKEND_URL` environment variable) are scheduled for a separate Deployment spec, after studio_ui works and is tested locally. | Requirement 6 fixes the bind address and the CORS origins to localhost. Changing them is a deployment decision, outside this spec. |

## File map

| Path | Status | Purpose |
|---|---|---|
| `engine/c_parser.py` | changed | Adds `parse_user_snippet` and private helpers. `parse` is not edited. |
| `engine/snippets.py` | new | The four demo names and sources, moved out of `engine/demo.py`. Text is byte-identical. |
| `engine/demo.py` | changed | Imports the snippets. Extends the two replay functions. The `run` path writes the Snapshot. The no-argument usage is unchanged. |
| `engine/replayed_state.py` | new | Pure Replayed_State builders and validator. |
| `engine/snapshot.py` | new | Snapshot schema, validator and atomic writer. Holds the only copy of the Snapshot path. |
| `engine/sim_runner.py` | new | Runs `make` with the snippet module, the file lock, the timeout and the error types. |
| `engine/bus_driver.py` | changed | Adds `peek(addr)`. |
| `tests/snippet_run.py` | new | cocotb module. Reads runs from a JSON file and writes records to a JSON file. Not named `test_*`. |
| `tests/demo_print.py` | deleted | Replaced by `tests/snippet_run.py`. |
| `tests/test_replayed_rtl.py` | new | cocotb tests on the real RTL, including the negative control. |
| `tests/Makefile` | changed | One line: the uart_ctrl `COCOTB_TEST_MODULES` gets `test_replayed_rtl` appended. |
| `tests/test_strict_parser.py`, `tests/test_count_lines.py`, `tests/test_replayed_state.py`, `tests/test_snapshot.py`, `tests/test_sim_runner.py`, `tests/test_backend_api.py`, `tests/test_backend_no_llm.py`, `tests/test_web_static.py` | new | pytest tests. No simulator needed. |
| `backend/__init__.py`, `backend/validation.py`, `backend/app.py`, `backend/requirements.txt` | new | Local FastAPI Backend. |
| `web/` (Next.js app, components, lib, tests) | new | The Studio. See section 6. |
| `web/public/demo_snapshot.json` | written by the engine | Never hand-written. |

## Data flow

1. The Studio sends a run request to the Backend: `{"snippet": NAME}` or `{"c_source": TEXT}`.
2. The Backend runs the checks in section 5.4. A User_Snippet passes through `parse_user_snippet` first.
3. The Backend takes the simulation lock and calls `run_replays`. That writes a runs file, runs `make COCOTB_TEST_MODULES=snippet_run` in `tests/`, and reads back one record.
4. `tests/snippet_run.py` replays the source on the RTL in quiet mode (seed None). It returns the exact report text and the Replayed_State.
5. The Backend returns `{"report": TEXT, "replayed_state": STATE_OR_NULL}`.
6. The Studio parses the body with the shared reader and displays the result.

For the Snapshot, the same `run_replays` call handles the four demo sources. The CLI then writes `web/public/demo_snapshot.json` only if all four records validate.
## 1. Engine: strict parser entry point (`engine/c_parser.py`)

### 1.1 Signature

```python
def parse_user_snippet(snippet: str) -> list[Operation]:
    """Return parse(snippet) unchanged, or raise ParseError with a 1-based line."""
```

- Raises `ParseError` (existing class, with `.line: int` and `.message: str`). `SymbolError` is a subclass and is also allowed.
- Helper `_safe_line(value) -> int` returns `value` when it is an int of at least 1, otherwise 1. Every raised error passes through it, so `line` is never 0, None, or a float.
- The existing `parse(snippet)` function is not edited.

### 1.2 What `parse()` accepts today

Checked against `engine/c_parser.py`. These inputs pass `parse()`, so the strict layer must reject them:

- `UART_ISR = (1U << RX_READY);`. `RX_READY` is in `REGISTERS`, so `bit_name_to_index` resolves it.
- Raw integer values: `UART_ISR = 5;` and `UART_ISR = 0x5 | 0x1;`. `_primary` accepts NUM tokens.
- Numeric bit indexes: `UART_ISR = (1U << 2);`. `_shift` accepts an index up to 31.
- Compound expressions: `UART_ISR = (1U << TX_DONE) | (1U << PARITY_ERR);`, and `~` applied to any operand.
- `uint16_t` declarations. `_TYPES` contains `uint16_t`.
- Statements with no handler. Top-level statements get `handler = ""`.
- Empty text. `parse("")` returns `[]`.
- An empty handler, `void h(void) {}`. It also returns `[]`, so the return value cannot tell it from empty text.
- Several handlers in one snippet, and UART_ISR and UART_RDR in one snippet.

### 1.3 Algorithm

Input: `snippet`. Output: the list from `parse()`, or a `ParseError`.

**Step 1, parse.** Run `ops = parse(snippet)`. If it raises `ParseError` `e`, add the candidate `(_safe_line(e.line), 0, e.message)` and set `ops = None`.

**Step 2, line scan.** Run `_scan_lines(snippet.splitlines())`. It returns `has_handler` and a list of `(line, message)` errors. Each scan error has priority 2.

*Note on U+2028.* Step 2 calls `_scan_lines(snippet.splitlines())` on purpose. Line 84 of `engine/c_parser.py` (`_tokenize`) also uses `splitlines()` for its line numbers. That file cannot be edited, so the scan must split the same way to report the same line numbers. The `count_lines` rule in Section 5.4 splits only on `\n`, after normalizing `\r\n` and `\r`. So a snippet that contains U+2028 counts as 1 line for the 200-line size check, but it splits into 2 lines for parser and line-scan numbering. This divergence is intended. Section 7.1 tests it.

**Step 3, no handler.** If `has_handler` is false, add the candidate `(1, 1, NO_HANDLER)`.

**Step 4, two registers.** Handled by the line scan (the `REG_NAME` rule in `_scan_lines`), not here. This step adds no candidate, so it cannot conflict with the scan. A later `parse()` error cannot hide an earlier second register.

**Step 5, choose.** Pick the candidate with the smallest `(line, priority)` and raise `ParseError(line, message)`. If there are no candidates, return `ops` unchanged.

The priority breaks ties on the same line. A `parse()` error beats the no-handler message, which beats the scan messages.

`_scan_lines(lines)`:

- State: `inside = False`, `open_line = 0`, `has_handler = False`, `errors = []`, `first_reg = None`, `both_reported = False`.
- For each line `raw` with 1-based number `n`:
  - `code = _strip_comments(raw).strip()`. `_strip_comments` is `re.sub(r"/\*.*?\*/", " ", raw).split("//", 1)[0]`, the same rule the tokenizer in `parse()` uses.
  - If `code` is empty, continue.
  - If `/*` or `*/` remains in `code`, add `(n, BLOCK_COMMENT)` and continue.
  - If `inside` is true, find every match, in order, of `REG_NAME` (`\b(UART_ISR|UART_RDR)\b`) in `code`. The first match sets `first_reg`. The first match whose name differs from `first_reg` adds `(n, BOTH_REGISTERS)` with priority 2 and sets `both_reported = True`. When `both_reported` is already true, add nothing. This check runs on every line inside a handler, including lines that also have a form error. It is the only place this candidate is made.
  - If `code` fully matches `HANDLER_EMPTY`, set `has_handler = True`. If `inside` is true, add `(n, NESTED)`. Continue.
  - If `code` fully matches `HANDLER_OPEN`, add `(n, NESTED)` when `inside` is true. Set `inside = True`, `open_line = n`, `has_handler = True`. Continue.
  - If `code == "}"`: when `inside`, set `inside = False`; otherwise add `(n, STRAY_BRACE)`. Continue.
  - If `code` starts with the word `void`, set `has_handler = True` and add `(n, HEADER_FORM)`. Continue. This makes a bad header count as a handler attempt.
  - If `not inside`, add `(n, OUTSIDE)`. Continue.
  - If any FORM pattern fully matches `code`, continue.
  - Otherwise add `(n, _reject_message(code))`.
- After the loop, if `inside` is still true, add `(open_line, NOT_CLOSED)`.

Patterns, compiled once in `engine/c_parser.py`. The form and handler patterns are used with `fullmatch` on `code`. The search patterns are used with `search`.

```python
import re

W = r"(?:TX_DONE|PARITY_ERR|OVERRUN_ERR)"

FORM_ASSIGN   = re.compile(r"UART_ISR\s*=\s*\(\s*1U\s*<<\s*" + W + r"\s*\)\s*;")
FORM_OR       = re.compile(r"UART_ISR\s*\|=\s*\(\s*1U\s*<<\s*" + W + r"\s*\)\s*;")
FORM_AND      = re.compile(r"UART_ISR\s*&=\s*~\s*\(\s*1U\s*<<\s*" + W + r"\s*\)\s*;")
FORM_DECL     = re.compile(r"(?:uint8_t|uint32_t)\s+[A-Za-z_]\w*\s*=\s*UART_(?:ISR|RDR)\s*;")
HANDLER_OPEN  = re.compile(r"void\s+[A-Za-z_]\w*\s*\(\s*void\s*\)\s*\{")
HANDLER_EMPTY = re.compile(r"void\s+[A-Za-z_]\w*\s*\(\s*void\s*\)\s*\{\s*\}")

RDR_WRITE      = re.compile(r"UART_RDR\s*[|&]?=")
ISR_WRITE      = re.compile(r"UART_ISR\s*[|&]?=")
REG_DECL_OTHER = re.compile(r"\w+\s+[A-Za-z_]\w*\s*=\s*UART_(?:ISR|RDR)\s*;")
REG_NAME       = re.compile(r"\b(UART_ISR|UART_RDR)\b")
```

In each pattern, a `|` is either the escaped literal `\|` (for `|=`) or an alternation `|` (for `uint8_t|uint32_t`, `ISR|RDR`, and the `W` group). Raw string literals keep the two meanings separate.

`_reject_message(code)` returns the first match:

1. `RDR_WRITE` matches: `UART_RDR is read-to-clear and cannot be written`.
2. `ISR_WRITE` matches and `\bRX_READY\b` is in `code`: `RX_READY is read-only and cannot be written; writable bits are TX_DONE, PARITY_ERR and OVERRUN_ERR`.
3. `ISR_WRITE` matches: `UART_ISR write is not an accepted form: use UART_ISR = (1U << NAME);, UART_ISR |= (1U << NAME); or UART_ISR &= ~(1U << NAME); with NAME TX_DONE, PARITY_ERR or OVERRUN_ERR`.
4. `REG_DECL_OTHER` matches: `a register read must be declared as uint8_t or uint32_t, for example uint8_t d = UART_RDR;`.
5. Otherwise: `statement does not match an accepted form`.

Message constants, all defined in `engine/c_parser.py`:

- `NO_HANDLER = "no handler definition: a User_Snippet must contain void NAME(void) { ... }"`
- `OUTSIDE = "statement outside a handler definition"`
- `BOTH_REGISTERS = "a User_Snippet may name only one register, UART_ISR or UART_RDR"`
- `BLOCK_COMMENT = "block comments must open and close on the same line"`
- `NESTED = "handler definitions cannot be nested"`
- `STRAY_BRACE = "'}' without an open handler definition"`
- `HEADER_FORM = "handler header must be void NAME(void) { with each statement on its own line"`
- `NOT_CLOSED = "handler definition is not closed with '}'"`

### 1.4 Precedence and line numbers (Requirement 3, criteria 14, 16, 17, 18)

| Snippet | Result | Rule |
|---|---|---|
| `""` or whitespace only | `ParseError(1, NO_HANDLER)` | No handler at all. Line 1. |
| `"void h(void) {}"` | `[]` | Valid. The header makes `has_handler` true. Replayed_State is null. |
| `"UART_ISR = (1U << TX_DONE);"` | `ParseError(1, NO_HANDLER)` | No handler. Line 1 wins over the outside-handler statement. |
| `"void h(void) {\n UART_ISR = (1U << TX_DONE);\n}\nUART_ISR = (1U << PARITY_ERR);"` | `ParseError(4, OUTSIDE)` | Handler exists. The statement on line 4 is outside it. |
| `"void h(void) {\n UART_ISR \|= (1U << RX_READY);\n}"` | `ParseError(2, RX_READY message)` | Scan error. |
| `"void h(void) {\n UART_ISR = 5;\n}"` | `ParseError(2, UART_ISR write message)` | Scan error. |
| `"void h(void) {\n UART_ISR = (1U << TX_DONE);\n uint8_t d = UART_RDR;\n}"` | `ParseError(3, BOTH_REGISTERS)` | Second register is on line 3. |
| `"void h(void) {\n UART_ISR = (1U << TX_DONE);\n uint8_t d = UART_RDR;\n for (;;) {}\n}"` | `ParseError(3, BOTH_REGISTERS)` | Parse fails later on line 4 (loop). The line scan still reports the earlier second register on line 3. |
| `"void h(void) {\n for (;;) {}\n}"` | `ParseError(2, loop message from parse)` | Parse error on line 2. |
| `"for (;;) {}"` | `ParseError(1, loop message from parse)` | Parse error and no handler, both on line 1. The parse error wins the tie. |
| `"void h(void) { UART_ISR = (1U << TX_DONE); }"` | `ParseError(1, HEADER_FORM)` | One-line handler with a statement is rejected. The header counts as a handler, so NO_HANDLER does not apply. |

### 1.5 Empty handler versus no handler

`parse()` returns `[]` for empty text and for an empty handler. The strict layer decides between them with `has_handler`. A `void` header line sets it, whether the header is empty or has the normal form. Empty text, whitespace, and comment-only text leave it false, so they get line 1.

### 1.6 Equivalence (Requirement 3, criterion 20)

An accepted snippet returns the list object from `parse()`. The strict layer never builds `Operation` objects, so the result is equal to `parse(snippet)` in content and in order.

### 1.7 Enforcement map

| Criterion | Enforced by |
|---|---|
| 1, 3 to 8 | FORM patterns on each statement line, plus `parse()` for values. |
| 9 (loop, if, ternary, call, pointer) | `parse()` raises. |
| 10 (statement matches no form) | `_reject_message` default. |
| 11 (write UART_RDR) | `parse()` raises. The RDR_WRITE message covers the same case. |
| 12 (unknown register) | `parse()` raises SymbolError. |
| 13 (RX_READY, other bit names, raw indexes, raw constants) | FORM patterns only accept TX_DONE, PARITY_ERR and OVERRUN_ERR with `1U`. |
| 14 (no handler) | Step 3, line 1. |
| 15 (both registers) | Line scan, `REG_NAME` rule: the first line inside a handler that names the second register. |
| 16 (outside a handler) | `_scan_lines` OUTSIDE. |
| 17 (first rejected statement only) | Step 5 returns one error. |
| 18 (1-based line, line 1 with no handler) | `_safe_line` and Step 3. |
| 19 (message names the form) | Messages in 1.3. |
| 20 (same operations) | Section 1.6. |

### 1.8 Known limits of the matcher

- One statement per line. A statement split across lines is rejected at its first line. This is a choice.
- Only `1U` is accepted as the constant, because the form in Requirement 3 uses `1U`. A plain `1` is rejected. This is a choice.
- Comments are `//` and single-line `/* */` only.
- Handler bodies are on their own lines. A one-line handler with a statement is rejected.

The matcher works on text lines. It never tokenizes or evaluates an expression. All values come from `parse()`.

## 2. Replayed_State and the replay paths

### 2.1 Shape

Replayed_State is a JSON object `{"register": "UART_ISR" | "UART_RDR", "pre": int, "post": int}`, or JSON `null`. Integer ranges: UART_ISR 0 to 15, UART_RDR 0 to 255. It sits next to the report and never inside it.

`engine/replayed_state.py` (pure Python, no cocotb):

```python
REGISTER_MAX = {"UART_ISR": 15, "UART_RDR": 255}

def make_replayed_state(register: str, pre: int, post: int) -> dict: ...   # validates, returns the dict
def validate_replayed_state(value) -> None: ...                           # None is allowed; raises ValueError
def isr_replayed_state(accesses: list[dict]) -> dict | None: ...
def rdr_replayed_state(pre: int, post: int) -> dict: ...
```

`accesses` entries are `{"kind": "READ" | "WRITE" | "RMW", "pre": int, "post": int}`. For READ, `pre` and `post` are the same value, since a read does not change UART_ISR. For WRITE and RMW, `pre` is the value sampled before the access, and `post` is the value sampled after the commit.

`isr_replayed_state`:

- Returns `None` when no WRITE or RMW entry exists. That covers empty handlers and reads-only snippets.
- Otherwise returns `make_replayed_state("UART_ISR", accesses[0]["pre"], accesses[-1]["post"])`.

Because `accesses[0]` can be a READ, `pre` is the value before the snippet's first access, as the Glossary requires.

`rdr_replayed_state(pre, post)` returns `make_replayed_state("UART_RDR", pre, post)`. It is never null. The RDR path only runs when the snippet contains a UART_RDR read.

### 2.2 UART_ISR path (`engine/demo.py`, `run_c_source`)

Today READ operations call `bus.read` and drop the value, and the trace records only WRITE and RMW. The change:

- Record every access in program order. For READ, use the value returned by `await bus.read(ISR_ADDR)`. For WRITE and RMW, use the existing pre and actual values.
- Build `accesses` from those records. Set `trace["accesses"] = accesses` and `trace["replayed_state"] = isr_replayed_state(accesses)`.
- `trace["ops"]` keeps its current content, so the existing cocotb tests still check the same values.
- The signature `run_c_source(dut, source, seed, trace=None)` does not change.

### 2.3 UART_RDR path (`engine/demo.py`, `run_c_rdr_source`)

Two new keyword parameters. Both default to the current behavior:

- `post_probe=None`: an async callable that returns an int. `None` means the real probe, `bus.peek(RDR_ADDR)`.
- `rx_on_read=None`: an int byte or `None`. When it is set, the standard `RDR_RX_DATA` pulse is skipped. The last READ in the snippet runs with `rx_valid=1` and `rx_data=rx_on_read` driven during its commit edge. `rx_valid` is lowered right after that read.

After the read loop:

- `pre = reads[0].value`, the value the first read returned before it cleared the register.
- `post = await post_probe()`. The default is the RTL sample taken right after the last read's commit edge.
- `trace["replayed_state"] = rdr_replayed_state(pre, post)`.

No branch replaces `post` with 0 or with `pre`. The value always comes from the probe.

### 2.4 `BusDriver.peek` (`engine/bus_driver.py`)

```python
async def peek(self, addr):
    """Return rdata without a read strobe, after the next falling edge."""
    self.dut.addr.value = addr
    self.dut.re.value = 0
    self.dut.we.value = 0
    await FallingEdge(self.dut.clk)
    return int(self.dut.rdata.value)
```

`peek` does not clear anything. `rdata` is combinational from `addr` and the register state, and `re` is not involved. In `rtl/uart_ctrl.sv`, lines 26 to 28 assign `rdata` from `sel_isr`, `sel_rdr`, `isr` and `rdr` only, with no `re` term. Call it right after the last access's commit edge, so the value is the state after that commit. `FallingEdge` is already imported in `bus_driver.py`.

### 2.5 Dispatch in the shared replay module (`tests/snippet_run.py`)

For each run in the input file:

1. `ops = parse(source)`.
2. If any op has `reg == "UART_RDR"`, call `run_c_rdr_source(dut, source, seed=None, trace=trace)`.
3. Otherwise call `run_c_source(dut, source, seed=None, trace=trace)`. This path also covers empty handlers and reads-only snippets, which give a null Replayed_State.
4. Append `{"name", "source", "report": report_text, "replayed_state": trace["replayed_state"]}`.

The module uses quiet runs only (seed None). Its only file output is the path in `REGSPECTRE_RUN_OUT`. It never opens `web/public/demo_snapshot.json`.

### 2.6 Negative control for the RDR post sample

The control is in `tests/test_replayed_rtl.py`, in `test_rdr_post_negative_control`. Its purpose is to show that a replay which assumes a post value fails the check. In `rtl/uart_ctrl.sv` line 47, `rdr_next = rx_valid ? rx_data : (rdr_read ? 8'd0 : rdr)`, so `rx_valid` wins over `rdr_read` on the same edge. Scenario A depends on that rule: its post value is 60, not 0.

A helper, `assert_rdr_post(state, expected_post)`, raises `AssertionError` when `state["post"] != expected_post`. The test runs two scenarios:

- Scenario A: `rx_on_read=0x3C`, source `void rd(void) {\n    uint8_t d = UART_RDR;\n}\n`.
  - Real probe: the check must pass with post 60.
  - Broken probe `assume_zero`, which always returns 0: the check must raise `AssertionError`.
- Scenario B: `RDR_DOUBLE_READ_SNIPPET`, quiet.
  - Real probe: the check must pass with post 0.
  - Broken probe `assume_pre`, which returns the first read value: the check must raise `AssertionError`, because 165 is not 0.

The test passes only when the real probe passes and both broken probes raise. If a broken probe passes, the test fails, which means the check cannot detect that bug.

### 2.7 Real RTL, quiet runs, Snapshot untouched

- Every replay goes through `tests/snippet_run.py` and `make`. Icarus Verilog and cocotb run the RTL. Quiet runs use seed None.
- Only the demo CLI can write `web/public/demo_snapshot.json` (section 3).
- The Backend never writes it (Requirement 6, criterion 2).

## 3. Snapshot writer (`engine/snapshot.py`)

### 3.1 JSON schema

```json
{
  "created_utc": "2026-11-15T12:00:00Z",
  "records": [
    {
      "name": "ISR_RMW_SNIPPET",
      "source": "void uart_isr(void) {\n    UART_ISR |= (1U << TX_DONE);\n}\n",
      "report": "[\n  {\n    \"register\": \"UART_ISR\", ...\n  }\n]",
      "replayed_state": {"register": "UART_ISR", "pre": 9, "post": 0}
    }
  ]
}
```

Rules:

- Top level: exactly the keys `created_utc` and `records`.
- `created_utc`: UTC time from `datetime.now(timezone.utc)`, formatted `YYYY-MM-DDTHH:MM:SSZ`.
- `records`: exactly four objects, in the order of `DEMO_SNIPPET_NAMES`. Each has exactly the keys `name`, `source`, `report`, `replayed_state`.
- `report`: a JSON string holding the exact text from `reports_to_json`. The Studio reads it with the same reader as the Backend response.
- `replayed_state`: an object or `null`, checked by `validate_replayed_state`.
- Text: `json.dumps(payload, indent=2) + "\n"`, UTF-8, LF line endings.

### 3.2 API

```python
REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = REPO_ROOT / "web" / "public" / "demo_snapshot.json"

def build_snapshot(records: list[dict], created_utc: str) -> dict: ...
def write_snapshot_atomic(path: Path, payload: dict) -> None: ...
```

`build_snapshot` checks the names and their order, the keys of each record, that `source` is a string, that `report` parses as a JSON list, that `replayed_state` is valid, and that `created_utc` has the required form. It raises `ValueError` on any failure. It does not touch the disk.

`write_snapshot_atomic`:

1. Render the text in memory. No file is touched yet.
2. Create the parent folder with `mkdir(parents=True, exist_ok=True)`. `web/public/` may not exist yet.
3. Write to `path.with_name(path.name + ".tmp")` with LF line endings, then `flush` and `fsync`.
4. `os.replace(tmp, path)`.
5. On any exception, remove the temp file if it exists, then re-raise.

Guarantees:

- Invalid records fail in `build_snapshot`, before any file work, so the existing snapshot keeps its exact bytes.
- A failure during the write or at the replace leaves the old file in place. `os.replace` is atomic within one filesystem.
- A failed replay never reaches `build_snapshot`, because `run_replays` raises first (section 4).

Only `engine/demo.py` `run_demo` calls the writer, after all four replays succeed and their records validate. No other CLI command and no Backend code path calls it. The literal text `demo_snapshot.json` appears only in `engine/snapshot.py`, and a test checks that (section 7.1).

## 4. Replay runner (`engine/sim_runner.py`)

The demo CLI and the Backend both use this module.

```python
MAKE_COMMAND = ["make"]                  # unit tests replace this with a fake command
TESTS_DIR = REPO_ROOT / "tests"
LOCK_PATH = TESTS_DIR / ".sim.lock"
SIM_MODULE = "snippet_run"

class SimulationBusy(Exception): ...
class SimulationTimeout(Exception): ...
class SimulationFailed(Exception):
    def __init__(self, message: str): self.message = message

def run_replays(runs: list[dict], timeout_s: float | None) -> list[dict]: ...
def flock_held() -> bool: ...
```

`run_replays(runs, timeout_s)`:

1. Check `runs`: a non-empty list of dicts with string `name` and string `source`. Otherwise raise `ValueError`.
2. Open `LOCK_PATH` with `os.open(..., O_CREAT | O_RDWR)`. Take `fcntl.flock(fd, LOCK_EX | LOCK_NB)`. If that raises `BlockingIOError`, raise `SimulationBusy`.
3. Create a temp directory. Write `runs.json` as `{"runs": runs}`. The output file is `out.json`. stdout and stderr go to files in the temp directory, not pipes, so a full pipe cannot block the child process.
4. Start `MAKE_COMMAND + ["COCOTB_TEST_MODULES=snippet_run"]` with `cwd=TESTS_DIR`, an environment that adds `REGSPECTRE_RUN_IN` and `REGSPECTRE_RUN_OUT`, and `start_new_session=True`.
5. `proc.wait(timeout=timeout_s)`. On `TimeoutExpired`:
   - `os.killpg(proc.pid, SIGTERM)`, then `proc.wait(5)`.
   - If the process is still alive, `os.killpg(proc.pid, SIGKILL)` and `proc.wait()`.
   - Raise `SimulationTimeout`.
   With `start_new_session`, `make` is the group leader, so the signal reaches `vvp` too.
6. If the return code is not 0, the message is the last non-empty line of the stderr file, or else of the stdout file. Newlines are removed and the text is cut to 300 characters. If both are empty, the message is `make exited with status N`. Raise `SimulationFailed`.
7. If `out.json` is missing, raise `SimulationFailed("the simulation finished without writing a result")`.
8. Parse `out.json`. The records must match `runs` in count and order. Each record needs the keys `name`, `source`, `report` (a string), and `replayed_state` (validated). Any mismatch raises `SimulationFailed("the simulation wrote an unreadable result")`.
9. In a `finally` block: `flock(LOCK_UN)`, close the descriptor, and remove the temp directory.

`flock_held()` opens `LOCK_PATH`, tries `LOCK_EX | LOCK_NB`, and returns True on `BlockingIOError`. Otherwise it unlocks and returns False. The descriptor is always closed.

The 60-second Backend budget covers the whole `make` run. That includes a rebuild of `sim.vvp` when the RTL changed. Measured on this repository (reported by the user): a cold `make clean` build plus the four-snippet `python3 -m engine.demo run` took 1.85 s (exit 0), and a warm run took 1.60 s (exit 0). That is a margin of more than 30 times inside the 60-second budget (O2 closed).

## 5. Backend (`backend/`)

### 5.1 Files

| File | Content |
|---|---|
| `backend/__init__.py` | Empty. |
| `backend/validation.py` | Pure request validation. Imports no FastAPI. |
| `backend/app.py` | The FastAPI app, routes, CORS, the simulation lock. |
| `backend/requirements.txt` | `fastapi`, `uvicorn`, and `httpx` (for `TestClient` in tests). |

`httpx` is not installed in `~/.venv` at present (reported). Install it from `backend/requirements.txt` before running `tests/test_backend_api.py`.

The Backend is outside `engine/` (D1). The engine scan in `tests/test_no_llm.py` stays on the engine files only, so it passes unchanged. The Backend imports `engine.c_parser`, `engine.snippets`, `engine.sim_runner`, and `engine.replayed_state`. The engine never imports `backend`.

### 5.2 Binding, CORS, start command

- Start the app from the repository root with uvicorn. The app object is `backend.app:app`. Bind the host to 127.0.0.1 and the port to 8000. Use one worker.
- `CORSMiddleware` with `allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"]`, `allow_methods=["GET", "POST"]`, `allow_headers=["Content-Type"]`, `allow_credentials=False`.
- A request from any other origin gets no `Access-Control-Allow-Origin` header.

### 5.3 Endpoints

| Route | Success | Errors |
|---|---|---|
| `GET /api/status` | 200 `{"busy": bool}` | none |
| `GET /api/snippets` | 200 `[{"name": str, "source": str}, ...]`, four entries in `DEMO_SNIPPET_NAMES` order, sources from `engine/snippets.py` | none |
| `POST /api/run` | 200 `{"report": str, "replayed_state": object or null}` | 400 `{"error":"too_large"}`; 400 `{"error":"invalid_request"}`; 422 `{"error":"parser_error","line":N,"message":M}`; 409 `{"error":"busy"}`; 504 `{"error":"timeout"}`; 500 `{"error":"simulation_failed","message":M}` |

The `POST /api/run` body is a JSON object with exactly one key: `snippet` (a Demo_Snippet name) or `c_source` (text). Anything else gets `invalid_request`. The body is read with `await request.body()` and parsed by hand. The app does not use a Pydantic body model, because FastAPI's default validation would return its own 422 and break the error codes above.

### 5.4 Validation order (`backend/validation.py`)

`validate_run_request(raw: bytes) -> RunRequest | ErrorReply` is a pure function. It runs three steps, and the app runs the fourth.

**Step 1, too_large (HTTP 400).** Decode the body as UTF-8 JSON. If it is an object whose `c_source` is a string, and that string is more than 8192 UTF-8 bytes, or `count_lines(c_source) > 200`, return 400 `{"error":"too_large"}`. Requirement 3, criterion 25.

`count_lines(text)` is the single line-counting rule. Python implements it in `backend/validation.py`. JavaScript implements it as `countLines` in `web/lib/snippetState.ts`. Both use the same four steps:

1. If `text` is empty, return 0.
2. Replace each `\r\n` with `\n`, then each remaining `\r` with `\n`.
3. If the result ends with `\n`, remove that one trailing `\n`.
4. Split on `\n` only, and return the number of parts. Python uses `len(text.split("\n"))`. JavaScript uses `text.split("\n").length`.

The rule does not use Python `str.splitlines()`. That method also splits on VT, FF, NEL and U+2028 (LINE SEPARATOR), but JavaScript does not. A U+2028 inside a line therefore counts as one line in both languages.

**Step 2, invalid_request (HTTP 400).** Return 400 `{"error":"invalid_request"}` when any of these holds:
- The body is not valid JSON, or it is not an object.
- The keys are not exactly `{"snippet"}` or exactly `{"c_source"}`.
- `snippet` is not one of the four Demo_Snippet names.
- `c_source` is not a string.

Requirement 6, criterion 5.

**Step 3, parser_error (HTTP 422).** When the key is `c_source`, call `parse_user_snippet(c_source)`. On `ParseError`, return 422 `{"error":"parser_error","line": e.line,"message": e.message}`. Requirement 3, criteria 21 and 22.

If all three steps pass, return a `RunRequest`:
- For `snippet`: `name` is the Demo name, and `source` is the demo source from `engine/snippets.py`.
- For `c_source`: `name` is `USER_SNIPPET`, and `source` is the text.

**Step 4, busy (HTTP 409), in the app.** Runs only after Steps 1 to 3 pass. `SIM_LOCK.acquire(blocking=False)` fails, so the response is 409. If the lock is free, `run_replays` takes the file lock. If that raises `SimulationBusy`, the response is also 409.

Steps 1 to 3 run before any lock in every case. So an invalid request gets the same 400 or 422 whether a simulation is running or not. A valid request gets 409 only when a simulation is running.

Order between the two 400 checks: too_large comes first. A request with both fields and an oversized `c_source` gets too_large.

### 5.5 Route handler and lock release (`backend/app.py`)

```python
SIM_LOCK = threading.Lock()
RUN_TIMEOUT_S = 60.0

@app.post("/api/run")
async def post_run(request: Request):
    raw = await request.body()
    checked = validate_run_request(raw)            # Steps 1 to 3
    if isinstance(checked, ErrorReply):
        return JSONResponse(checked.body, status_code=checked.status)
    if not SIM_LOCK.acquire(blocking=False):       # Step 4
        return busy_response()
    try:
        records = await run_in_threadpool(run_replays, [checked.as_run()], RUN_TIMEOUT_S)
    except SimulationBusy:
        return busy_response()
    except SimulationTimeout:
        return JSONResponse({"error": "timeout"}, status_code=504)
    except SimulationFailed as exc:
        return JSONResponse({"error": "simulation_failed", "message": one_line(exc.message)}, status_code=500)
    except Exception:
        return JSONResponse({"error": "simulation_failed", "message": "the backend hit an unexpected error"}, status_code=500)
    else:
        record = records[0]
        return JSONResponse({"report": record["report"], "replayed_state": record["replayed_state"]}, status_code=200)
    finally:
        SIM_LOCK.release()

@app.get("/api/status")
async def get_status():
    return {"busy": SIM_LOCK.locked() or flock_held()}
```

- `finally` releases `SIM_LOCK` on every path. `run_replays` releases the file lock in its own `finally`.
- `one_line(text)` replaces newlines with spaces, trims, and cuts to 300 characters.
- The status route reads both locks. It never blocks.

### 5.6 Timeout and termination

- `RUN_TIMEOUT_S = 60`. The timer covers the whole `make` run (section 4, step 5).
- On timeout, the Backend sends SIGTERM to the process group, waits 5 seconds, then sends SIGKILL if needed. It returns 504 and no report.
- A timed-out request is never retried.

### 5.7 Concurrency, network, and no-LLM statement

- One uvicorn worker. A second request during a run gets 409 from the thread lock, before any file lock work.
- The CLI (`python3 -m engine.demo run`) and the Backend both take `tests/.sim.lock`. Only one of them can run a simulation at a time. The CLI exits with status 1 and a message when the lock is busy, instead of waiting.
- The Backend makes no LLM call and no outbound network call. Its only external effect is starting `make` in `tests/`, which runs Icarus Verilog locally. It imports no HTTP client.
- `tests/test_backend_no_llm.py` scans `backend/` with the rules from `tests/test_no_llm.py`. That scan is static. It checks imports and eval/exec calls only.

## 6. Studio (`web/`)

### 6.1 Stack and file layout

Next.js with the App Router, React, and TypeScript. Tests use Vitest with React Testing Library and jsdom. Exact package versions are set in `web/package.json` when the implementation task runs. No part of this design depends on a version.

| File | Responsibility |
|---|---|
| `web/package.json`, `tsconfig.json`, `next.config.mjs`, `vitest.config.ts` | Tooling. |
| `web/app/layout.tsx` | Root HTML layout. |
| `web/app/page.tsx` | Renders the client component `StudioPage`. |
| `web/app/StudioPage.tsx` | State owner: sources, backend status, shown result, run action, page layout. |
| `web/components/CodePane.tsx` | Textarea and the demo name label. |
| `web/components/SnippetSelector.tsx` | The four demo names, in order. |
| `web/components/RunControl.tsx` | Run button and its enabled rule. |
| `web/components/RegisterArray.tsx` | Register selector and the 32 cells. |
| `web/components/ViolationList.tsx` | Source label, rows, and the empty text. |
| `web/components/WaveformPlaceholder.tsx` | Fixed region with the placeholder text only. |
| `web/components/Disclaimers.tsx` | Always-visible disclaimers and the replayed-state notes. |
| `web/components/Message.tsx` | Message area for errors and for states with no results. |
| `web/lib/config.ts` | Backend URL, timings, and size limits. |
| `web/lib/messages.ts` | Every user-visible string taken from the requirements. |
| `web/lib/types.ts` | `Violation`, `Replayed`, `Snapshot`, and result types. |
| `web/lib/reader.ts` | The shared reader and schema validator (6.2). |
| `web/lib/api.ts` | Fetch wrappers with timers. |
| `web/lib/poller.ts` | Status polling loop. |
| `web/lib/sources.ts` | Demo snippet source loading (Backend, then Snapshot). |
| `web/lib/snippetState.ts` | Demo or user derivation, run body, size check. |
| `web/lib/runState.ts` | Shown-state type and the outcome mapping (6.5). |
| `web/lib/registerCells.ts` | The 32-cell model. Pure function. |
| `web/public/demo_snapshot.json` | Written by `python3 -m engine.demo run`. Never hand-written. |

### 6.2 Shared reader (`web/lib/reader.ts`)

One module reads every Backend response body and every Snapshot record. This covers Requirement 8, criterion 6, and Requirement 9, criterion 4.

Each exported function returns `{ ok: true, value }` or `{ ok: false }`. None throws.

- `parseReportText(text: string)`. The text must be a JSON array. Each element must be an object whose keys are exactly `register`, `bit`, `intended`, `actual`, `cycle`, plus `c_line` when present. Checks:
  - `register` is `UART_ISR` or `UART_RDR`.
  - `bit` is an integer from 0 to the width minus 1: 3 for UART_ISR (width 4), 7 for UART_RDR (width 8).
  - `intended` and `actual` are 0 or 1.
  - `cycle` is an integer of at least 0.
  - `c_line`, when present, is an integer of at least 1.
  Returns `Violation[]`.
- `parseReplayedState(value: unknown)`. Accepts `null`. Otherwise the value must be an object with exactly the keys `register`, `pre`, `post`. `pre` and `post` are integers from 0 to 15 for UART_ISR and from 0 to 255 for UART_RDR. Returns `Replayed | null`.
- `parseRunBody(text: string)`. The text must be a JSON object with exactly the keys `report` and `replayed_state`. `report` goes through `parseReportText`, and `replayed_state` goes through `parseReplayedState`. Returns `{ violations, replayed }`.
- `parseSnapshot(text: string)`. The text must be a JSON object with exactly the keys `created_utc` and `records`. `created_utc` matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`. `records` has four objects whose names are in DEMO order. Each record has exactly the keys `name`, `source`, `report`, `replayed_state`. `source` is a string. `report` and `replayed_state` go through the same functions as above. Returns `{ createdUtc, records }`.
- `parseSnippetList(text: string)`. A JSON array of four objects `{name, source}`, in DEMO order.
- `parseErrorResponse(status: number, text: string)`. Returns a typed reply for a non-200 response (6.5). Never throws. A 409 whose body is not `{"error":"busy"}`, and a 504 whose body is not `{"error":"timeout"}`, return the unreadable reply. That reply maps to `CANNOT_READ` (Requirement 9, criterion 4), with no results and no recorded output.

Rules: no `eval` and no dynamic code. Text from the Backend is only rendered as text. It is cut to 500 characters, and newlines are replaced with spaces.

### 6.3 Backend client (`web/lib/api.ts`)

- `fetchStatus()`: `GET /api/status` with an AbortController that aborts after 2000 ms. Returns `{kind: "reachable", busy}` for any HTTP response. `busy` comes from the body when it is a boolean, otherwise `false`. Returns `{kind: "unreachable"}` when the request is aborted or fails at the network layer.
- `postRun(body)`: `POST /api/run` with an AbortController that aborts after 70000 ms. Returns `{kind: "response", status, text}`, or `{kind: "no_response"}`.
- `fetchSnippets()`: `GET /api/snippets` with a 2000 ms abort. Returns the text, or `null`.
- `loadSnapshot()`: `fetch("/demo_snapshot.json", {cache: "no-store"})`. Returns the text, or `null` when the fetch fails or the status is not 200.

Timers use AbortController with `setTimeout`, not `AbortSignal.timeout`. That lets the jsdom tests use fake timers.

### 6.4 Status polling (`web/lib/poller.ts`)

- The loop waits for each status outcome before it schedules the next one. Each outcome is passed to the page.
- Interval: the next request starts 1000 ms after the previous one started. If the previous request took longer than 1000 ms, the next one starts immediately.
- Backend state: `unknown` until the first outcome, then `reachable` with `busy`, or `unreachable`. `unreachable` is exactly the case where the latest status request got no HTTP response within 2000 ms (Requirement 8, criterion 10).
- Polling stops when the page unmounts.

### 6.5 Run actions and outcome mapping (`web/lib/runState.ts`)

Shown-state type:

```ts
type Shown =
  | { kind: "empty" }                                       // nothing shown: labels only
  | { kind: "message"; text: string }                       // a message and no results
  | { kind: "live"; violations: Violation[]; replayed: Replayed | null }
  | { kind: "recorded"; createdUtc: string; violations: Violation[]; replayed: Replayed | null };
```

Starting a run: `pending = true` and `shown = empty`. This clears the previous run (Requirement 9, criterion 7).

Client-side size check for user snippets: more than 200 lines or more than 8192 UTF-8 bytes gives `shown = message(TOO_LARGE)` and sends no request (Requirement 3, criterion 24).

Request routing:

| Backend state | Snippet | Result |
|---|---|---|
| `unreachable` | demo | Recorded output from the Snapshot record with the same name (Requirement 8, criterion 11). If the Snapshot fails the reader (Requirement 8, criterion 16), show `RECORDED_UNAVAILABLE`. |
| `unreachable` | user | Show `UNREACHABLE_USER` (Requirement 8, criterion 15). No recorded output. |
| `unknown` | either | Run control is disabled, so no request is sent. |
| `reachable` | either | `POST /api/run`. The outcome table below applies. |

Outcome of `POST /api/run`:

| Outcome | Result |
|---|---|
| `no_response` (70 s elapsed, or a network failure before any response) | `NO_RESPONSE` (Requirement 7, criterion 10). |
| 200, valid body | `live` with the parsed violations and replayed state. |
| 200, invalid body | `CANNOT_READ` (Requirement 9, criterion 4). |
| 400 `too_large` | `TOO_LARGE` (Requirement 9, criterion 8). |
| 400 `invalid_request`, or any other 400 body | `REJECTED` (Requirement 9, criterion 9). Treating other 400 bodies this way is a choice. |
| 409 `busy` | `BUSY` (Requirement 7, criterion 7). |
| 409, other body | `CANNOT_READ` (Requirement 9, criterion 4). |
| 422 `parser_error` with a valid line and message | `"Line " + line + ": " + message` (Requirement 3, criterion 23). |
| 422, other body | `CANNOT_READ` (Requirement 9, criterion 4). |
| 500 `simulation_failed` with a message | `SIMULATION_FAILED_PREFIX + message` (Requirement 9, criterion 3). |
| 500, other body | `CANNOT_READ` (Requirement 9, criterion 13). |
| 504 `timeout` | `TIMEOUT` (Requirement 7, criterion 9). |
| 504, other body | `CANNOT_READ` (Requirement 9, criterion 4). |
| any other status | `UNEXPECTED_STATUS_PREFIX + status` (Requirement 9, criterion 5). |

No error response ever produces recorded output (Requirement 9, criterion 6). Recorded output appears only on the unreachable path, which means the latest status request had no HTTP response.

### 6.6 Source loading (`web/lib/sources.ts`)

On mount:

1. `fetchSnippets()`. If the list parses with `parseSnippetList`, use those sources (Requirement 2, criterion 7).
2. For each demo name still missing, use the source from `loadSnapshot()` after `parseSnapshot`. This covers Requirement 2, criteria 8 and 9.
   Choice: the Snapshot is used for sources only when the whole file passes `parseSnapshot`. A bad record in the file then removes the Snapshot sources too.
3. If the selected demo name still has no source, the code pane shows `SOURCES_UNAVAILABLE` (Requirement 2, criterion 10).

Initial code: once the ISR_RMW source is known, the code pane holds it and ISR_RMW is selected (Requirement 2, criteria 2 and 3). Until then the pane is empty.

### 6.7 Demo or user derivation (`web/lib/snippetState.ts`)

- `demoNameFor(code, selected, sources)` returns `selected` when `sources[selected] === code`, using exact string equality. Otherwise it returns `null` (Requirement 2, criteria 5 and 7).
- `runBody(code, demoName)` returns `{snippet: demoName}` when `demoName` is not null, otherwise `{c_source: code}` (Requirement 2, criterion 6).
- `countLines(text)` in `web/lib/snippetState.ts` implements the rule in 5.4. The client-side size check in 6.5 uses `countLines(code) > 200` and the UTF-8 byte length above 8192.
- After an edit, the selector keeps its selection. The name label disappears, because the text no longer matches the source (Requirement 2, criterion 5).

### 6.8 Run control (`web/components/RunControl.tsx`)

Enabled when all of these hold:
- No run is pending.
- The backend state is `unreachable`, or it is `reachable` and not busy.

Disabled when a run is pending, the backend state is `unknown`, or the backend is busy (Requirement 7, criteria 4 and 5).

When the backend is unreachable, a user snippet stays enabled. Its outcome is the message in 6.5.

### 6.9 Recorded-output text rule

Recorded output must not show the word "live" in any letter case (Requirement 8, criterion 13). The test is a case-insensitive substring match, so a word such as "delivered" also fails. Recorded output renders "Recorded output, created " followed by the stored `created_utc` text. The recorded-view test (section 7.4) fails if any text node matches `/live/i`. Disclaimers and messages are checked too.

### 6.10 Register array (`web/lib/registerCells.ts`, `web/components/RegisterArray.tsx`)

`buildRegisterCells(register, shown): Cell[32]` is a pure function.

- `width` is 4 for UART_ISR and 8 for UART_RDR.
- Names: UART_ISR gives `TX_DONE`, `RX_READY`, `PARITY_ERR`, `OVERRUN_ERR`. UART_RDR gives `RDR[0]` to `RDR[7]`.
- For cell `i` from 0 to 31:
  - If `i >= width`, the cell is `{index: i, unused: true, label: "unused", lines: [], violation: false}`. Requirement 5, criteria 8, 9, 10.
  - Otherwise the label is the bit name. Lines are computed as follows:
    - `shown` is `empty` or `message`: `lines = []`. Requirement 5, criterion 11.
    - `shown` is `live` or `recorded`:
      - If `replayed` is null or `replayed.register !== register`, push `NOT_REPLAYED`. Requirement 5, criterion 15.
      - Otherwise push `"pre " + ((pre >> i) & 1) + ", post " + ((post >> i) & 1)`. Requirement 5, criterion 13.
      - Let `matches` be the violations with `register === register` and `bit === i`. If `matches` is not empty, set `violation = true` and push one `"intended " + intended + ", actual " + actual` line per match, in array order. Requirement 5, criterion 12. Otherwise push `NO_VIOLATION_REPORTED`. Requirement 5, criterion 14.

Unused cells never get lines or the violation flag (Requirement 5, criterion 10). Only violations of the selected register are used for the cells, and the list still shows all of them (Requirement 5, criterion 16).

Register selector: UART_ISR is selected on load (Requirement 5, criterion 4). Changing the selector runs `buildRegisterCells` again on the current `shown` value. No request is sent (Requirement 5, criterion 5).

Rendering: a 32-cell grid. Each cell shows its index, its label, and its lines. A violation cell gets a visible class and the text `VIOLATION_MARK` (the word "violation"), so the mark does not depend on colour alone.

### 6.11 Violation list (`web/components/ViolationList.tsx`)

- Source label, shown directly above the list:
  - `live`: `LIVE_LABEL` ("Live result").
  - `recorded`: `RECORDED_LABEL_PREFIX + createdUtc`, which is "Recorded output, created " followed by the stored `created_utc` text, copied exactly.
  - `empty` or `message`: no label (Requirement 1, criteria 5 to 7).
- For `live` or `recorded`:
  - If `violations` is empty, show `NO_VIOLATIONS` and no rows (Requirement 4, criterion 7).
  - Otherwise show one row per element, in array order, with columns register, bit, intended, actual, cycle, and c_line. A missing c_line shows `NOT_FROM_C` (Requirement 4, criteria 1 to 5).
- For `empty` and `message`, no rows are shown. Messages appear in the message area (6.12).

### 6.12 Message area and code pane messages

- `Message` renders `shown.text` when `shown.kind` is `message`.
- `SOURCES_UNAVAILABLE` appears in the code pane area (Requirement 2, criterion 10).
- `RECORDED_UNAVAILABLE` (Requirement 8, criterion 16) and `UNREACHABLE_USER` (Requirement 8, criterion 15) appear in the message area.

### 6.13 Disclaimers (`web/components/Disclaimers.tsx`)

- Always rendered in a plain list. Never inside a collapsed or hidden element (Requirement 10, criterion 9). The five texts are the ones in Requirement 10, criteria 1 to 5, copied word for word.
- Shown only when `shown.kind` is `live` or `recorded` and `replayed` is not null: the texts of Requirement 10, criteria 10 and 11, copied word for word.

### 6.14 Layout and waveform slot (`web/app/StudioPage.tsx`, `web/components/WaveformPlaceholder.tsx`)

CSS grid areas:

- `header`: the disclaimers.
- `code`: the code pane, the selector, the run control, and the code pane message.
- `results`: the register selector and array, the source label, the violation list, and the message area.
- `waveform`: the fixed slot.

The waveform slot has a fixed grid area and a fixed height in CSS, so changes to the results never move it (Requirement 1, criterion 2).

`WaveformPlaceholder` renders only the text `WAVEFORM_PLACEHOLDER` ("Waveform view is not available in this version."). It has no inputs, no buttons, and no data (Requirement 1, criteria 3 and 4).

### 6.15 Constants and timers (`web/lib/config.ts`)

```ts
export const BACKEND_URL = "http://127.0.0.1:8000";
export const STATUS_INTERVAL_MS = 1000;
export const STATUS_TIMEOUT_MS = 2000;
export const RUN_TIMEOUT_MS = 70000;
export const MAX_LINES = 200;
export const MAX_BYTES = 8192;
```

These values match Requirement 7. The Backend stops a simulation after 60 seconds, and the Studio gives up after 70, so a Backend 504 normally arrives before the Studio's own timeout.

### 6.16 Messages (`web/lib/messages.ts`)

Every string below is copied exactly from the requirements. Only this file holds them. Tests compare rendered text with these constants.

| Constant | Text |
|---|---|
| `NO_RESPONSE` | No response arrived within 70 seconds. The Backend may still be running the simulation. No results are shown. |
| `BUSY` | A simulation is already running. Try again when it finishes. |
| `TIMEOUT` | The simulation ran longer than 60 seconds and was stopped. No partial results are shown. |
| `SIMULATION_FAILED_PREFIX` | The simulation failed: |
| `CANNOT_READ` | The backend returned a response the Studio cannot read. No results are shown. |
| `REJECTED` | The backend rejected the run request. No results are shown. |
| `TOO_LARGE` | The snippet is larger than 200 lines or 8 KB and was not run. |
| `UNEXPECTED_STATUS_PREFIX` | The backend returned an unexpected status |
| `UNREACHABLE_USER` | The backend is unreachable. User snippets need the backend. |
| `RECORDED_UNAVAILABLE` | The recorded output could not be loaded. |
| `SOURCES_UNAVAILABLE` | The demo snippet sources could not be loaded. |
| `WAVEFORM_PLACEHOLDER` | Waveform view is not available in this version. |
| `LIVE_LABEL` | Live result |
| `RECORDED_LABEL_PREFIX` | Recorded output, created |
| `NO_VIOLATIONS` | The report contains no violations. |
| `NOT_FROM_C` | not from C |
| `NO_VIOLATION_REPORTED` | no violation reported |
| `NOT_REPLAYED` | not replayed |
| `VIOLATION_MARK` | violation |
| `UNUSED` | unused |
| `LINE_PREFIX` | Line |

The three prefix constants are joined with the values as described in 6.5. For example, `UNEXPECTED_STATUS_PREFIX` plus the status number gives the requirement's text.

The disclaimers in 6.13 are kept in the same file, under the names `DISCLAIMER_1` to `DISCLAIMER_5` and `REPLAYED_NOTE_1` and `REPLAYED_NOTE_2`.

### 6.17 Before the first status response

Run control is disabled while the backend state is `unknown`. Recorded output is not used until a status request has failed (Requirement 8, criterion 10). Demo sources may already be loaded from the Backend or from the Snapshot.

### 6.18 Safety

- No `dangerouslySetInnerHTML`, no `eval`, and no `new Function`.
- Absolute URLs in `web/` source may appear only for `BACKEND_URL` and for the localhost origins. Section 7.5 checks this.
- The Backend's error text is shown as plain text and is cut to 500 characters.

## 7. Testing strategy

### 7.1 Pure Python (pytest, no simulator)

| File | Covers |
|---|---|
| `tests/test_strict_parser.py` | `parse_user_snippet`: each error type (loop, if/else, ternary, call, pointer, UART_RDR write, unknown register, unknown bit, RX_READY, raw constant, raw index, compound expression, `uint16_t`, no handler, empty text, statement outside a handler, both registers, block comment, header form, unclosed handler). Line numbers and the precedence table in 1.4, including the line-scan case in which a second register on line 3 is reported before a loop on line 4 (`ParseError(3, BOTH_REGISTERS)`). An empty handler returns `[]`. U+2028 divergence (intended): a snippet made of `void h(void) {`, a literal U+2028 character, ` UART_ISR = (1U << TX_DONE);`, another U+2028 character, and `}` has `count_lines` equal to 1, but `parse_user_snippet` accepts it and the WRITE op has c_line 2, because `splitlines()` splits on U+2028. The same snippet with ` for (;;) {}` in place of the statement gives `ParseError(2, loop message)`. Equality with `parse()` for accepted inputs. The four demo sources are accepted. Hypothesis: for any text, the result is either a list equal to `parse()` output, or a `ParseError` with an int line of at least 1 and a str message. Hypothesis: snippets generated from the accepted forms equal `parse()` output and never raise. |
| `tests/test_count_lines.py` | `count_lines` in Python and `countLines` in Vitest (section 7.4), on the same inputs and with the same results: empty text gives 0; `x` gives 1; a trailing `\n` gives 1; `\r\n` gives 1; a lone `\r` gives 1; `\n\n` gives 2; U+2028 between two words gives 1, not 2; 200 lines gives 200 and is accepted; 201 lines gives 201 and is rejected by the Backend and by the Studio. |
| `tests/test_replayed_state.py` | `isr_replayed_state`: empty gives None, reads only gives None, write pre and post, read then write takes pre from the read, RMW. `rdr_replayed_state`. `validate_replayed_state`: bool values rejected, UART_ISR pre 16 rejected, UART_RDR post 256 rejected, None accepted, wrong keys rejected. |
| `tests/test_snapshot.py` | `build_snapshot`: schema, order, wrong names rejected. `write_snapshot_atomic` success. Failure with `os.replace` monkeypatched to raise: the original bytes are kept and the temp file is removed. Invalid records: the file is untouched, and a missing file stays missing. The literal `demo_snapshot.json` appears only in `engine/snapshot.py`. |
| `tests/test_sim_runner.py` | `run_replays` with `MAKE_COMMAND` replaced by a fake script: success writes the result, a non-zero exit gives `SimulationFailed` with the last stderr line, a timeout kills the whole process group (a fake child process must be gone afterwards), a held lock gives `SimulationBusy`, and the lock is free again after each case. |
| `tests/test_backend_no_llm.py` | Scans `backend/` with the forbidden-name rules from `tests/test_no_llm.py`. The scanner is imported from that module. |
| `tests/test_web_static.py` | Scans `web/` source for absolute URLs. Only `BACKEND_URL` and the localhost origins are allowed. |

The existing `tests/test_no_llm.py`, `tests/test_engine_unit.py`, and `tests/test_engine_props.py` do not change. The scanner in `test_no_llm.py` also covers the new engine files, and they import no forbidden name.

### 7.2 Backend API (`tests/test_backend_api.py`, FastAPI `TestClient`)

`run_replays` is replaced by fakes in these tests.

Before running this file, install `httpx` from `backend/requirements.txt`. It is not installed in `~/.venv` at present (reported). Without it, FastAPI's `TestClient` cannot be imported.

- Order matrix: every combination of busy or not busy, with oversized, bad field, parser error, and valid requests. Each one gets the status and body from section 5.4.
- A valid request while busy gets 409 `{"error":"busy"}`. A bad name gets 400. An oversized snippet gets 400. A parser error gets 422.
- `GET /api/status` is false at start, and true while `SIM_LOCK` is held.
- `GET /api/snippets` returns four entries in order, with sources equal to `engine/snippets.py`.
- A successful `POST /api/run` returns exactly the keys `report` and `replayed_state`. The `report` string equals the fake text byte for byte.
- A fake `SimulationTimeout` gives 504 `{"error":"timeout"}`, with no `report` key.
- A fake `SimulationFailed("line one\nline two")` gives 500, with the message `line one line two`.
- A fake `SimulationBusy` gives 409.
- A fake `RuntimeError` gives 500 `simulation_failed`. The next valid request then reaches `run_replays` again, which shows the lock was released.
- Invalid JSON, a non-object body, an extra key, both fields, neither field, and an unknown name all give 400 `invalid_request`.
- CORS: a preflight from `http://localhost:3000` gets the allow-origin header. A preflight from another origin gets none.
- The Snapshot path, patched to a temp file, is not created or changed by any run.
- The text `0.0.0.0` appears nowhere in `backend/`.
- Line-count boundaries: 200 lines pass, and 201 lines give 400 `too_large`. The inputs match `tests/test_count_lines.py`, including a U+2028 line separator, which must count as one line.

### 7.3 Real RTL (cocotb): `tests/test_replayed_rtl.py`

The module is added to the uart_ctrl `COCOTB_TEST_MODULES` line in `tests/Makefile`. The default count goes from 33 to 40, because there are seven new tests. Every test uses quiet runs.

Guardrail (O5, mitigated on paper, pending the Makefile change and the first run): `tests/test_replayed_rtl.py` may define only `@cocotb.test()` coroutines, and helpers whose names do not start with `test_`. Existing cocotb modules expose only `@cocotb.test()` coroutines. With no `pytest.ini`, `pyproject.toml`, or `setup.cfg`, `pytest --collect-only -q tests/` collected 100 tests cleanly (reported by the user). After adding the module to the Makefile list, run `pytest tests/` again to confirm that collection stays clean.

| Test | Input | Expected Replayed_State |
|---|---|---|
| `test_isr_rmw_replayed_state` | `ISR_RMW_SNIPPET` | pre 9, post 0 |
| `test_isr_direct_replayed_state` | `ISR_DIRECT_SNIPPET` | pre 9, post 8 |
| `test_isr_read_only_replayed_state_is_null` | `void rd(void) {\n    uint32_t s = UART_ISR;\n}\n` | null, and report `[]` |
| `test_rdr_double_read_replayed_state` | `RDR_DOUBLE_READ_SNIPPET` | pre 165, post 0 |
| `test_rdr_single_read_replayed_state` | `RDR_SINGLE_READ_SNIPPET` | pre 165, post 0 |
| `test_rdr_post_measured_after_rx_on_read` | `uint8_t d = UART_RDR;` with `rx_on_read=0x3C` | pre 0, post 60 |
| `test_rdr_post_negative_control` | the two scenarios in 2.6 with the broken probes | each broken run must raise `AssertionError` |

These expected values are derived from the next-state rules in `rtl/uart_ctrl.sv`. They are not yet confirmed by a run. The first run must confirm them. If one differs, the test is wrong or the RTL is, and the cause must be found before the value is changed.

### 7.4 Frontend (Vitest)

| File | Covers |
|---|---|
| `web/__tests__/reader.test.ts` | `parseReportText`: valid array, `c_line` absent, `c_line` 0 rejected, UART_RDR bit 8 rejected, `intended` 2 rejected, extra key rejected. `parseReplayedState`: null accepted, UART_ISR pre 16 rejected. `parseRunBody`: exact keys. `parseSnapshot`: wrong order rejected, bad `created_utc` rejected, a record with a bad report rejected by the same reader. `parseErrorResponse`: each status, each body shape, and non-JSON text without throwing. A 409 whose body is not `{"error":"busy"}`, and a 504 whose body is not `{"error":"timeout"}`, both return the unreadable reply, which maps to `CANNOT_READ`, with no results and no recorded output. |
| `web/__tests__/registerCells.test.ts` | 32 cells. UART_ISR cells 4 to 31 are unused, with no 0, no 1, and no violation, replayed, or "no violation reported" text. UART_RDR cells 8 to 31 are unused. Empty `shown` gives labels only. `replayed` null gives "not replayed". A register mismatch gives "not replayed". A flagged cell lists its pairs in array order and is marked. An unflagged cell shows "no violation reported". Pre and post bit values. |
| `web/__tests__/runState.test.ts` | Every row of the outcome table in 6.5. 409 and 504 show no results. Unreachable demo shows recorded output with the exact label. Unreachable user shows the message and no recorded output. Error bodies never produce recorded output. A 409 with a body other than busy, and a 504 with a body other than timeout, each show `CANNOT_READ` with no results and no recorded output. `no_response` shows the 70-second message and no recorded output. |
| `web/__tests__/snippetState.test.ts` | Demo derivation by exact equality. One changed character makes a user snippet. Run body shapes. The `countLines` cases from 7.1, with the same inputs and results as the Python function, including U+2028 counting as one line. The size limit at exactly 200 and 201 lines, and at 8192 and 8193 bytes. |
| `web/__tests__/poller.test.ts` (fake timers) | The next request starts 1000 ms after the previous one. A request aborted at 2000 ms gives `unreachable`. A non-200 response gives `reachable`. |
| `web/__tests__/disclaimers.test.tsx` | The five disclaimers are always rendered. The two replayed notes appear only when replayed state is shown. |
| `web/__tests__/recordedText.test.tsx` | Renders the recorded state. No text node matches `/live/i`. |
| `web/__tests__/violationList.test.tsx` | The source label for live and recorded. The empty text. "not from C". Row order. |

### 7.5 Static checks

- `tests/test_no_llm.py` (unchanged): scans `engine/` for forbidden imports and for eval or exec calls.
- `tests/test_backend_no_llm.py`: the same rules for `backend/`.
- `tests/test_web_static.py`: absolute URLs in `web/` source, except for `BACKEND_URL` and the localhost origins.

### 7.6 Properties checked by the tests

- P1. For every accepted snippet, `parse_user_snippet(s) == parse(s)`, in content and order.
- P2. Every `ParseError` from `parse_user_snippet` has an int line of at least 1 and a str message.
- P3. A failed snapshot write leaves the existing file's bytes unchanged.
- P4. A request that fails Steps 1 to 3 gets the same answer whether a simulation is running or not. A request that passes them gets 409 when a simulation is running.

### 7.7 Limits

- Hypothesis and the other randomized tests sample inputs. Passing them is not proof that the parser or the RTL is correct.
- The no-LLM scans read imports and eval/exec calls in source text. They do not stop network use at run time.
- The C subset is small. Nothing here claims to run general C.
- The RTL is the uart_ctrl block only. Results do not describe a whole chip, and cycle numbers count clock edges in the simulation only.
- The frontend tests check the reader and the state logic with examples. They do not drive a real browser.
- The Backend binds to 127.0.0.1 and has no authentication. It is for local use.

## 8. Demo CLI, snippet module, and requirements coverage

### 8.1 `engine/snippets.py`

Holds `DEMO_SNIPPET_NAMES` (the four names in order), the four source constants, and `DEMO_SOURCES`, a tuple of `(name, source)` pairs in the same order. The source text is copied byte for byte from `engine/demo.py`. `engine/demo.py` imports these names, so `tests/test_demo.py` keeps working unchanged.

### 8.2 `engine/demo.py`

- No-argument usage: unchanged.
- `run`: builds `runs` from `DEMO_SOURCES`, calls `run_replays(runs, timeout_s=None)`, validates the records, calls `build_snapshot` and `write_snapshot_atomic(SNAPSHOT_PATH, ...)`, then prints the records in the existing format. Exit status 0 only when all of these succeed.
- If the lock is busy, the CLI prints "another simulation is running" and exits with status 1. A failed replay prints the message and exits with status 1, and it writes nothing.
- The old `REGSPECTRE_DEMO_OUT` mechanism is removed with `tests/demo_print.py`.

### 8.3 `tests/Makefile`

One change, to the uart_ctrl `COCOTB_TEST_MODULES` line: append `,test_replayed_rtl`. The `COCOTB_TEST_MODULES=snippet_run` override is passed on the command line, so the module is not in the default list.

### 8.4 Requirements coverage

| Requirement | Design sections |
|---|---|
| 1 Studio layout | 6.11, 6.13, 6.14 |
| 2 Demo snippets | 6.5, 6.6, 6.7 |
| 3 User C and parser errors | 1, 5.4, 6.5, 6.11 |
| 4 Violation list | 6.11 |
| 5 Register array | 6.10 |
| 6 Live Backend | 5.2 to 5.5, 2.5 |
| 7 Single simulation and timeout | 4, 5.5, 5.6, 6.5, 6.8 |
| 8 Recorded snapshot | 3, 6.2, 6.5, 6.9 |
| 9 Error states | 6.2, 6.5 |
| 10 Wording and claims | 6.13, 6.16 |
| Replayed_State (Glossary) | 2 |

---

## 9. Choices made where the requirements are silent

- C1. The Backend lives in `backend/`, outside `engine/`, so the existing no-LLM scan stays unchanged.
- C2. `tests/demo_print.py` is retired. One replay module, `tests/snippet_run.py`, serves the demo CLI and the Backend. Requirement 6, criterion 1 says "the demo run path" for the snippet field. This design reads that as the shared replay path, not as the CLI. Approved (O4).
- C3. The strict parser is a line matcher on top of `parse()`. One statement per line. Only `1U` as the constant. One-line handlers with a statement are rejected.
- C4. An empty handler and an empty snippet are told apart by a `void` header line. Both give `parse()` the value `[]`.
- C5. Where a no-handler error and another error both sit on line 1, the parse error wins, then the no-handler error, then the scan errors.
- C6. The two 400 checks run in this order: too_large, then invalid_request. This follows the decision in the instructions. The requirements do not state an order between them.
- C7. A body that is not valid JSON, or that has extra keys, gets invalid_request.
- C8. Any 400 body that is neither too_large nor invalid_request shows the REJECTED message.
- C9. An unexpected exception in the Backend's run path gives 500 `simulation_failed` with the text "the backend hit an unexpected error".
- C10. The 60-second run budget covers the whole `make` run, including a rebuild of `sim.vvp` when the RTL changed. Measured timing is in section 4 (O2 closed).
- C11. A network failure before any response during a run shows the 70-second NO_RESPONSE message. That message says "within 70 seconds" even when the failure was immediate. Accepted as a limitation (O1 closed).
- C12. A non-200 status response counts as reachable, with busy set to false.
- C13. The snapshot is used for sources only if the whole file passes `parseSnapshot`.
- C14. For UART_ISR, pre comes from the first access, which may be a read, and post comes from the last access.
- C15. A snippet with an empty handler, or with reads only, has a null Replayed_State.
- C16. `post_probe` and `rx_on_read` are added to `run_c_rdr_source` for tests only. Their defaults give today's behavior.
- C17. The demo CLI writes the Snapshot before it prints, and it exits with status 1 if the write fails.
- C18. `tests/.sim.lock` is shared by the CLI and the Backend. The CLI fails fast when the lock is busy. The file should be added to `.gitignore`, which is not part of this design.
- C19. A flagged cell shows the text "violation" as well as the mark.
- C20. Run control stays disabled while the backend state is `unknown`.
- C21. Status polling starts each request 1000 ms after the previous one started.
- C22. Vitest and React Testing Library are used. No package version is fixed here.
- C23. Each unused cell shows the word "unused" and nothing else.
- C24. A request body with unknown extra keys is rejected, as in C7.
- C25. The two-register check is done by the line scan (`REG_NAME`), not after `parse()`, so a later parse error cannot hide an earlier second-register line.

## 10. Open items

### Resolved

- O1. Closed as an accepted limitation. Requirement 7, criterion 10 specifies one NO_RESPONSE message for no response during a run. Keeping choice C11 avoids reopening a locked requirement.
- O2. Closed. Measured on this repository: a cold `make clean` build plus the four-snippet `python3 -m engine.demo run` took 1.85 s (exit 0). A warm run took 1.60 s (exit 0). The margin is more than 30 times inside the 60-second budget.
- O3. Approved. Deleting `tests/demo_print.py` (D2, C2).
- O4. Approved. `tests/snippet_run.py` is the single shared replay path for Requirement 6, criterion 1 and for the demo CLI (C2).
- O5. Mitigated on paper, pending Makefile change (guardrail in section 7.3). `pytest --collect-only -q tests/` collected 100 tests cleanly, with no `pytest.ini`, `pyproject.toml`, or `setup.cfg` (reported by the user). The rules for `tests/test_replayed_rtl.py`, and the re-check after adding it, are in 7.3.

### Remaining verification (not yet run)

- Confirm the seven expected cocotb Replayed_State values in section 7.3 on the first real RTL run. The values are derived from the rules in `rtl/uart_ctrl.sv` (lines 26 to 28 for `rdata`, line 47 for `rdr_next`), not from a run.
- Install `httpx` from `backend/requirements.txt` before running `tests/test_backend_api.py`. It is not installed in `~/.venv` at present (reported).
- Run the `count_lines` tests in Python and Vitest, and the line-scan case for `BOTH_REGISTERS` in section 1.4, once the implementation exists.
