import { NOT_FROM_C } from "../lib/messages";
import type { Violation } from "../lib/types";

// The bit names of UART_ISR, from rtl/uart_ctrl.sv. UART_RDR bits are shown as RDR[n].
const ISR_FIELDS = ["TX_DONE", "RX_READY", "PARITY_ERR", "OVERRUN_ERR"];

function fieldName(violation: Violation): string {
  if (violation.register === "UART_ISR") {
    return ISR_FIELDS[violation.bit] ?? "";
  }
  return "RDR[" + violation.bit + "]";
}

// One card per violation, in report order. Shown above the Violation_List table, which is unchanged.
export function BugReportCards(props: { violations: Violation[] }) {
  return (
    <section aria-label="Bug reports">
      <div className="bug-card-list">
        {props.violations.map((violation, n) => (
          <article key={n} className="bug-card">
            <p className="mono">
              {violation.register} bit {violation.bit} {fieldName(violation)}
            </p>
            <p className="mono">
              cycle {violation.cycle}; C line {violation.c_line ?? NOT_FROM_C}
            </p>
            <div className="bug-card-values">
              <span className="value-pill value-expected">Expected {violation.intended}</span>
              <span className="value-pill value-actual">Actual {violation.actual}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
