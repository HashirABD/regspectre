import { UNUSED, VIOLATION_MARK } from "../lib/messages";
import type { Cell } from "../lib/registerCells";
import type { Register, Replayed } from "../lib/types";

// Access type of each register bit, from rtl/uart_ctrl.sv. The same source as RegisterMap.
const ACCESS: Record<Register, string> = { UART_ISR: "W1C", UART_RDR: "RTC" };

function bitOf(word: number, index: number): number {
  return (word >> index) & 1;
}

// Each bit is one tile: violation (flagged), clean (replayed bit changed, no violation), unchanged, or unused.
export function RegisterArray(props: {
  register: Register;
  onRegisterChange: (register: Register) => void;
  cells: Cell[];
  replayed?: Replayed | null;
}) {
  const replayedHere =
    props.replayed !== undefined && props.replayed !== null && props.replayed.register === props.register
      ? props.replayed
      : null;

  return (
    <div className="register-array">
      <select
        aria-label="Register"
        value={props.register}
        onChange={(event) =>
          props.onRegisterChange(event.target.value === "UART_RDR" ? "UART_RDR" : "UART_ISR")
        }
      >
        <option value="UART_ISR">UART_ISR</option>
        <option value="UART_RDR">UART_RDR</option>
      </select>
      <div className="cell-grid">
        {props.cells.map((cell) => {
          const changed =
            replayedHere !== null &&
            !cell.unused &&
            bitOf(replayedHere.pre, cell.index) !== bitOf(replayedHere.post, cell.index);
          const state = cell.unused
            ? "unused"
            : cell.violation
              ? "violation"
              : changed
                ? "clean"
                : "unchanged";
          return (
            <div
              key={cell.index}
              className={"cell cell-" + state}
              data-state={state}
              data-unused={cell.unused ? "true" : undefined}
              data-violation={cell.violation ? "true" : undefined}
            >
              <div className="cell-head">
                <span className="cell-index">{cell.index}</span>
                {cell.unused ? null : <span className="cell-access">{ACCESS[props.register]}</span>}
              </div>
              <div className="cell-label">{cell.unused ? UNUSED : cell.label}</div>
              {cell.violation ? <div className="cell-mark">{VIOLATION_MARK}</div> : null}
              {cell.lines.map((line, n) => (
                <div key={n} className={line.startsWith("pre ") ? "cell-line cell-transition" : "cell-line"}>
                  {line}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
