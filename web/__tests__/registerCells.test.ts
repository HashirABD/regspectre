import { describe, it, expect } from "vitest";
import { buildRegisterCells, type Cell, type Shown } from "../lib/registerCells";
import { NOT_REPLAYED, NO_VIOLATION_REPORTED, TOO_LARGE, UNUSED } from "../lib/messages";
import type { Replayed, Violation } from "../lib/types";

const ISR_LABELS = ["TX_DONE", "RX_READY", "PARITY_ERR", "OVERRUN_ERR"];
const RDR_LABELS = ["RDR[0]", "RDR[1]", "RDR[2]", "RDR[3]", "RDR[4]", "RDR[5]", "RDR[6]", "RDR[7]"];
const ALL_INDEXES = Array.from({ length: 32 }, (_, i) => i);

const EMPTY: Shown = { kind: "empty" };
const ISR_PRE9: Replayed = { register: "UART_ISR", pre: 9, post: 0 };
const ISR_FLAG_BIT3: Violation = { register: "UART_ISR", bit: 3, intended: 1, actual: 0, cycle: 3 };

function usedCells(cells: Cell[]): Cell[] {
  return cells.filter((cell) => !cell.unused);
}

// An unused cell shows only the word "unused": no value, no flag, no replayed text, no violation text.
function expectUnused(cell: Cell): void {
  expect(cell.unused).toBe(true);
  expect(cell.label).toBe(UNUSED);
  expect(cell.lines).toStrictEqual([]);
  expect(cell.violation).toBe(false);
  const text = [cell.label, ...cell.lines].join("|");
  expect(text).not.toMatch(/[01]|violation|replayed|no violation reported/i);
}

describe("buildRegisterCells", () => {
  it("returns 32 cells indexed 0 to 31 for both registers", () => {
    for (const register of ["UART_ISR", "UART_RDR"] as const) {
      const cells = buildRegisterCells(register, EMPTY);
      expect(cells).toHaveLength(32);
      expect(cells.map((cell) => cell.index)).toStrictEqual(ALL_INDEXES);
    }
  });

  it("UART_ISR cells 4 to 31 are unused and show no values or flags", () => {
    const shown: Shown = {
      kind: "live",
      violations: [
        { register: "UART_ISR", bit: 3, intended: 1, actual: 0, cycle: 3 },
        { register: "UART_ISR", bit: 5, intended: 1, actual: 0, cycle: 4 },
        { register: "UART_ISR", bit: 31, intended: 0, actual: 1, cycle: 5 },
      ],
      replayed: { register: "UART_ISR", pre: 15, post: 0 },
    };
    const cells = buildRegisterCells("UART_ISR", shown);
    for (const cell of cells.slice(4)) {
      expectUnused(cell);
    }
  });

  it("UART_RDR cells 8 to 31 are unused and show no values or flags", () => {
    const shown: Shown = {
      kind: "live",
      violations: [{ register: "UART_RDR", bit: 7, intended: 1, actual: 0, cycle: 2 }],
      replayed: { register: "UART_RDR", pre: 255, post: 0 },
    };
    const cells = buildRegisterCells("UART_RDR", shown);
    for (const cell of cells.slice(8)) {
      expectUnused(cell);
    }
  });

  it("UART_RDR cells 0 to 7 are labelled RDR[0] to RDR[7]", () => {
    const cells = buildRegisterCells("UART_RDR", EMPTY);
    expect(cells.slice(0, 8).map((cell) => cell.label)).toStrictEqual(RDR_LABELS);
  });

  it("UART_ISR cells 0 to 3 are labelled TX_DONE, RX_READY, PARITY_ERR, OVERRUN_ERR", () => {
    const cells = buildRegisterCells("UART_ISR", EMPTY);
    expect(cells.slice(0, 4).map((cell) => cell.label)).toStrictEqual(ISR_LABELS);
  });

  it("empty shown gives labels only", () => {
    const isrUsed = usedCells(buildRegisterCells("UART_ISR", EMPTY));
    expect(isrUsed.map((cell) => cell.label)).toStrictEqual(ISR_LABELS);
    expect(isrUsed.map((cell) => cell.lines)).toStrictEqual([[], [], [], []]);
    expect(isrUsed.map((cell) => cell.violation)).toStrictEqual([false, false, false, false]);

    const rdrUsed = usedCells(buildRegisterCells("UART_RDR", EMPTY));
    expect(rdrUsed.map((cell) => cell.label)).toStrictEqual(RDR_LABELS);
    expect(rdrUsed.map((cell) => cell.lines)).toStrictEqual(RDR_LABELS.map(() => []));
    expect(rdrUsed.map((cell) => cell.violation)).toStrictEqual(RDR_LABELS.map(() => false));
  });

  it("message shown gives labels only, the same as empty", () => {
    const message: Shown = { kind: "message", text: TOO_LARGE };
    expect(buildRegisterCells("UART_ISR", message)).toStrictEqual(buildRegisterCells("UART_ISR", EMPTY));
    expect(buildRegisterCells("UART_RDR", message)).toStrictEqual(buildRegisterCells("UART_RDR", EMPTY));
  });

  it("live view with null replayed gives not replayed and no violation reported on each used cell", () => {
    const shown: Shown = { kind: "live", violations: [], replayed: null };
    const used = usedCells(buildRegisterCells("UART_ISR", shown));
    expect(used.map((cell) => cell.lines)).toStrictEqual([
      [NOT_REPLAYED, NO_VIOLATION_REPORTED],
      [NOT_REPLAYED, NO_VIOLATION_REPORTED],
      [NOT_REPLAYED, NO_VIOLATION_REPORTED],
      [NOT_REPLAYED, NO_VIOLATION_REPORTED],
    ]);
    expect(used.map((cell) => cell.violation)).toStrictEqual([false, false, false, false]);
  });

  it("register mismatch gives not replayed and no violation", () => {
    const shown: Shown = {
      kind: "live",
      violations: [],
      replayed: { register: "UART_RDR", pre: 255, post: 255 },
    };
    const used = usedCells(buildRegisterCells("UART_ISR", shown));
    expect(used.map((cell) => cell.lines)).toStrictEqual([
      [NOT_REPLAYED, NO_VIOLATION_REPORTED],
      [NOT_REPLAYED, NO_VIOLATION_REPORTED],
      [NOT_REPLAYED, NO_VIOLATION_REPORTED],
      [NOT_REPLAYED, NO_VIOLATION_REPORTED],
    ]);
    expect(used.map((cell) => cell.violation)).toStrictEqual([false, false, false, false]);
  });

  it("pre and post bits come from the replayed state", () => {
    // 9 is binary 1001: bits 0 and 3 are 1, bits 1 and 2 are 0. Post is 0 everywhere.
    const shown: Shown = { kind: "live", violations: [], replayed: ISR_PRE9 };
    const used = usedCells(buildRegisterCells("UART_ISR", shown));
    expect(used.map((cell) => cell.lines)).toStrictEqual([
      ["pre 1, post 0", NO_VIOLATION_REPORTED],
      ["pre 0, post 0", NO_VIOLATION_REPORTED],
      ["pre 0, post 0", NO_VIOLATION_REPORTED],
      ["pre 1, post 0", NO_VIOLATION_REPORTED],
    ]);
  });

  it("a flagged cell lists its intended and actual pair after the pre and post line and is marked", () => {
    const shown: Shown = { kind: "live", violations: [ISR_FLAG_BIT3], replayed: ISR_PRE9 };
    const cells = buildRegisterCells("UART_ISR", shown);
    expect(cells[3]).toStrictEqual({
      index: 3,
      unused: false,
      label: "OVERRUN_ERR",
      lines: ["pre 1, post 0", "intended 1, actual 0"],
      violation: true,
    });
  });

  it("two violations on the same bit are listed in array order", () => {
    const violations: Violation[] = [
      { register: "UART_ISR", bit: 3, intended: 1, actual: 0, cycle: 7 },
      { register: "UART_ISR", bit: 3, intended: 0, actual: 1, cycle: 3 },
    ];
    const shown: Shown = { kind: "live", violations, replayed: ISR_PRE9 };
    const cells = buildRegisterCells("UART_ISR", shown);
    expect(cells[3]).toStrictEqual({
      index: 3,
      unused: false,
      label: "OVERRUN_ERR",
      lines: ["pre 1, post 0", "intended 1, actual 0", "intended 0, actual 1"],
      violation: true,
    });
  });

  it("an unflagged cell in a live view shows no violation reported after its pre and post line", () => {
    const shown: Shown = { kind: "live", violations: [ISR_FLAG_BIT3], replayed: ISR_PRE9 };
    const cells = buildRegisterCells("UART_ISR", shown);
    expect(cells[0]).toStrictEqual({
      index: 0,
      unused: false,
      label: "TX_DONE",
      lines: ["pre 1, post 0", NO_VIOLATION_REPORTED],
      violation: false,
    });
  });

  it("a violation of the other register does not flag the cell", () => {
    const shown: Shown = {
      kind: "live",
      violations: [{ register: "UART_RDR", bit: 3, intended: 1, actual: 0, cycle: 2 }],
      replayed: ISR_PRE9,
    };
    const cells = buildRegisterCells("UART_ISR", shown);
    expect(cells[3]).toStrictEqual({
      index: 3,
      unused: false,
      label: "OVERRUN_ERR",
      lines: ["pre 1, post 0", NO_VIOLATION_REPORTED],
      violation: false,
    });
  });

  it("recorded gives the same cells as live for the same replayed state and violations", () => {
    const violations: Violation[] = [ISR_FLAG_BIT3];
    const live: Shown = { kind: "live", violations, replayed: ISR_PRE9 };
    const recorded: Shown = {
      kind: "recorded",
      createdUtc: "2025-01-01T00:00:00Z",
      violations,
      replayed: ISR_PRE9,
    };
    expect(buildRegisterCells("UART_ISR", recorded)).toStrictEqual(buildRegisterCells("UART_ISR", live));
    expect(buildRegisterCells("UART_ISR", live)[3].violation).toBe(true);
  });
});
