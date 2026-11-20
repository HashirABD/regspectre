# RegSpectre

RegSpectre is a hardware-firmware co-verification tool. It replays the register accesses that C firmware handlers perform against the real SystemVerilog UART RTL (`rtl/uart_ctrl.sv`), driven through cocotb on Icarus Verilog. It then reports each register bit that changed without the firmware intending it, with the bit index, the C line, and the clock cycle.

Built with Kiro for Kiroween 2026.

## How it works

- `engine/c_parser.py` parses a small C subset into register operations.
- `engine/bus_driver.py` drives the RTL bus through cocotb.
- `engine/detector.py` compares intended and actual register state.
- `backend/` is a local FastAPI service on 127.0.0.1 that runs the engine.
- `web/` is the Studio (Next.js). It shows the engine's reports and holds no verification logic.

Every check in `engine/` is deterministic Python. No LLM call decides whether a bug exists.

## Tier 1 scope

Tier 1 implements two hardware bug classes. Each has a buggy demo snippet and a safe negative control, so four demo snippets cover them.

1. **W1C Read-Modify-Write (RMW) neighbor wipeout** on `UART_ISR`. `ISR_RMW_SNIPPET` (`UART_ISR |= (1U << TX_DONE);`) is the buggy form. Its negative control is `ISR_DIRECT_SNIPPET` (`UART_ISR = (1U << TX_DONE);`). A read-modify-write writes back the other pending bits as 1, which clears them in a write-one-to-clear register.
2. **Read-to-Clear (RTC) destructive double-read** on `UART_RDR`. `RDR_DOUBLE_READ_SNIPPET` reads `UART_RDR` twice, and the second read sees the cleared value. Its negative control is `RDR_SINGLE_READ_SNIPPET`, which reads once.

The full project scope is 4 bug classes. The remaining 2 bug classes are planned for Tier 2.

A replay covers one snippet on the `uart_ctrl` block. It does not simulate a whole chip, and a clean result does not prove that the UART is correct.

## Run locally

Prerequisites: Python 3 with cocotb 2.x, Hypothesis and pytest; Icarus Verilog; Node.js 22. Install the Backend packages with `pip install -r backend/requirements.txt`, and the Studio packages with `npm install` in `web/`.

Run the Python tests from the repository root:

pytest -q tests/


To regenerate the recorded demo output, run `python3 -m engine.demo run`. It replays the four demo snippets and writes `web/public/demo_snapshot.json`.

Start the Backend from the repository root in one terminal. Uvicorn listens on 127.0.0.1 port 8000 by default, so the Backend stays local:

uvicorn backend.app:app


Start the Studio in a second terminal:

cd web && npm test && npm run build && npm run start -- -H 127.0.0.1 -p 3000


Open `http://127.0.0.1:3000`. The Studio reaches the Backend only at `http://127.0.0.1:8000`.

## Project files

- `docs/KIRO_LOG.md`: the build log.
- `.kiro/specs/studio_ui/`: the requirements, design and tasks for the Studio.
