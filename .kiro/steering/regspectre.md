# RegSpectre project context

RegSpectre is a co verification tool. It drives real SystemVerilog RTL with cocotb on Icarus Verilog and replays the register accesses that C firmware would perform, then reports every bit that changed without the firmware intending it.

## Rules for the engine

1. Every check in engine/ is deterministic Python. No LLM call may decide whether a bug exists.
2. The RTL is the source of truth for register behavior. Never classify register bits by pattern matching netlists.
3. A violation is reported as intended state versus actual state, with the exact bit index, the C line, and the clock cycle.
4. The UI in web/ only displays reports from the engine. It contains no verification logic.

## Environment

1. Everything runs inside WSL Ubuntu with the Python virtual environment at ~/.venv.
2. Simulator is Icarus Verilog with cocotb 2.x. Property tests use Hypothesis and pytest.
3. Repository layout is rtl/ for SystemVerilog, firmware/ for C drivers, engine/ for Python, tests/ for cocotb and pytest, web/ for the Next.js studio.
