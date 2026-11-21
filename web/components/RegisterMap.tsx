import type { Register, Replayed } from "../lib/types";
import type { Shown } from "../lib/registerCells";

type Access = "W1C" | "RTC" | "RW" | "RO";

// The access type of each register, from rtl/uart_ctrl.sv. UART_ISR bits are write-one-to-clear, and UART_RDR is read-to-clear.
const REGISTERS: { name: Register; access: Access; width: number }[] = [
  { name: "UART_ISR", access: "W1C", width: 4 },
  { name: "UART_RDR", access: "RTC", width: 8 },
];

function accessClass(access: Access): string {
  if (access === "W1C") {
    return "badge-access badge-w1c";
  }
  if (access === "RTC") {
    return "badge-access badge-rtc";
  }
  if (access === "RW") {
    return "badge-access badge-rw";
  }
  return "badge-access badge-ro";
}

// Hex text with as many digits as the register width needs.
function hex(value: number, width: number): string {
  return "0x" + value.toString(16).toUpperCase().padStart(Math.ceil(width / 4), "0");
}

// Selecting a row only changes which register is inspected. It sends no run request.
export function RegisterMap(props: {
  register: Register;
  shown: Shown;
  onSelectRegister: (register: Register) => void;
}) {
  const shown = props.shown;
  const violations = shown.kind === "live" || shown.kind === "recorded" ? shown.violations : [];
  const replayed: Replayed | null = shown.kind === "live" || shown.kind === "recorded" ? shown.replayed : null;

  return (
    <table className="register-map" aria-label="Register map">
      <thead>
        <tr>
          <th scope="col">Register</th>
          <th scope="col">Access</th>
          <th scope="col">Status</th>
          <th scope="col">Pre</th>
          <th scope="col">Post</th>
          <th scope="col">Violations</th>
        </tr>
      </thead>
      <tbody>
        {REGISTERS.map((reg) => {
          const count = violations.filter((violation) => violation.register === reg.name).length;
          const replayedHere = replayed !== null && replayed.register === reg.name;
          const selected = props.register === reg.name;
          return (
            <tr
              key={reg.name}
              aria-selected={selected}
              tabIndex={0}
              onClick={() => props.onSelectRegister(reg.name)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  props.onSelectRegister(reg.name);
                }
              }}
            >
              <td className="mono">{reg.name}</td>
              <td>
                <span className={accessClass(reg.access)}>{reg.access}</span>
              </td>
              <td>{replayedHere ? "Replayed" : "Not replayed"}</td>
              <td className="mono">
                {replayed !== null && replayedHere ? hex(replayed.pre, reg.width) : "--"}
              </td>
              <td className="mono">
                {replayed !== null && replayedHere ? hex(replayed.post, reg.width) : "--"}
              </td>
              <td>
                <span className={count > 0 ? "pill pill-bug" : "pill pill-muted"}>
                  {count === 1 ? "1 violation" : count + " violations"}
                </span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
