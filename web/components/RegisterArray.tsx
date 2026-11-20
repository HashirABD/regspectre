import { UNUSED, VIOLATION_MARK } from "../lib/messages";
import type { Cell } from "../lib/registerCells";
import type { Register } from "../lib/types";

export function RegisterArray(props: {
  register: Register;
  onRegisterChange: (register: Register) => void;
  cells: Cell[];
}) {
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
        {props.cells.map((cell) => (
          <div
            key={cell.index}
            className={cell.violation ? "cell cell-violation" : "cell"}
            data-unused={cell.unused ? "true" : undefined}
            data-violation={cell.violation ? "true" : undefined}
          >
            <div className="cell-index">{cell.index}</div>
            <div className="cell-label">{cell.unused ? UNUSED : cell.label}</div>
            {cell.violation ? <div className="cell-mark">{VIOLATION_MARK}</div> : null}
            {cell.lines.map((line, n) => (
              <div key={n} className="cell-line">
                {line}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
