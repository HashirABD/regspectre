import { NOT_REPLAYED, NO_VIOLATION_REPORTED, UNUSED } from "./messages";
import type { Register, Replayed, Violation } from "./types";

// One of the 32 cells of the Register_Array (design 6.10, Requirement 5).
export type Cell = { index: number; unused: boolean; label: string; lines: string[]; violation: boolean };

// The state the Studio shows (design 6.5). Defined here because buildRegisterCells reads it.
export type Shown =
  | { kind: "empty" }
  | { kind: "message"; text: string }
  | { kind: "live"; violations: Violation[]; replayed: Replayed | null }
  | { kind: "recorded"; createdUtc: string; violations: Violation[]; replayed: Replayed | null };

const CELL_COUNT = 32;

// Bit names by register. The length of each list is the width of that register.
const BIT_NAMES: Record<Register, string[]> = {
  UART_ISR: ["TX_DONE", "RX_READY", "PARITY_ERR", "OVERRUN_ERR"],
  UART_RDR: ["RDR[0]", "RDR[1]", "RDR[2]", "RDR[3]", "RDR[4]", "RDR[5]", "RDR[6]", "RDR[7]"],
};

// Builds the 32 cells for the selected register from the shown state. Pure function (design 6.10).
export function buildRegisterCells(register: Register, shown: Shown): Cell[] {
  const names = BIT_NAMES[register];
  const width = names.length;
  const cells: Cell[] = [];

  for (let i = 0; i < CELL_COUNT; i += 1) {
    if (i >= width) {
      cells.push({ index: i, unused: true, label: UNUSED, lines: [], violation: false });
      continue;
    }

    const cell: Cell = { index: i, unused: false, label: names[i], lines: [], violation: false };

    if (shown.kind === "live" || shown.kind === "recorded") {
      const replayed = shown.replayed;
      if (replayed === null || replayed.register !== register) {
        cell.lines.push(NOT_REPLAYED);
      } else {
        cell.lines.push("pre " + ((replayed.pre >> i) & 1) + ", post " + ((replayed.post >> i) & 1));
      }

      const matches = shown.violations.filter((v) => v.register === register && v.bit === i);
      if (matches.length > 0) {
        cell.violation = true;
        for (const match of matches) {
          cell.lines.push("intended " + match.intended + ", actual " + match.actual);
        }
      } else {
        cell.lines.push(NO_VIOLATION_REPORTED);
      }
    }

    cells.push(cell);
  }

  return cells;
}
