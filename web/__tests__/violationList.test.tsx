import { describe, it, expect, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { ViolationList } from "../components/ViolationList";
import { LIVE_LABEL, NOT_FROM_C, NO_VIOLATIONS, RECORDED_LABEL_PREFIX } from "../lib/messages";
import type { Shown } from "../lib/registerCells";
import type { Violation } from "../lib/types";

const CREATED_UTC = "2026-11-15T12:00:00Z";
const WITH_LINE: Violation = { register: "UART_ISR", bit: 3, intended: 1, actual: 0, cycle: 4, c_line: 7 };
const WITHOUT_LINE: Violation = { register: "UART_ISR", bit: 3, intended: 1, actual: 0, cycle: 4 };

function bitViolation(bit: number): Violation {
  return { register: "UART_ISR", bit, intended: 1, actual: 0, cycle: 10 + bit, c_line: 5 };
}

afterEach(() => {
  cleanup();
});

function renderList(shown: Shown): HTMLElement {
  const { container } = render(<ViolationList shown={shown} />);
  return container;
}

// The header cell texts, in order, from the thead row.
function headerTexts(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll("thead th")).map((th) => th.textContent ?? "");
}

// The text of the named column in every body row, in row order. The column index comes from the header row.
function columnTexts(container: HTMLElement, column: string): string[] {
  const index = headerTexts(container).indexOf(column);
  if (index < 0) {
    throw new Error("no column named " + column);
  }
  return Array.from(container.querySelectorAll<HTMLTableRowElement>("tbody tr")).map((row) => {
    const cell = row.querySelectorAll("td").item(index);
    if (cell === null) {
      throw new Error("row has no cell at index " + index);
    }
    return cell.textContent ?? "";
  });
}

describe("ViolationList", () => {
  it("Requirement 1 criterion 5: a live view shows the source label Live result directly above the table", () => {
    const container = renderList({ kind: "live", violations: [WITH_LINE], replayed: null });
    const label = screen.getByText(LIVE_LABEL);
    const table = container.querySelector("table");
    if (table === null) {
      throw new Error("expected a table");
    }
    expect(label.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING).toBeGreaterThan(0);
  });

  it("Requirement 1 criterion 6: a recorded view shows the label RECORDED_LABEL_PREFIX plus createdUtc directly above the table", () => {
    const container = renderList({
      kind: "recorded",
      createdUtc: CREATED_UTC,
      violations: [WITH_LINE],
      replayed: null,
    });
    const label = screen.getByText(RECORDED_LABEL_PREFIX + CREATED_UTC);
    const table = container.querySelector("table");
    if (table === null) {
      throw new Error("expected a table");
    }
    expect(label.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING).toBeGreaterThan(0);
  });

  it("Requirement 1 criterion 7: an empty view shows no source label and no table", () => {
    const container = renderList({ kind: "empty" });
    expect(screen.queryByText(LIVE_LABEL)).toBeNull();
    expect(screen.queryByText(RECORDED_LABEL_PREFIX, { exact: false })).toBeNull();
    expect(container.querySelector("table")).toBeNull();
  });

  it("Requirement 1 criterion 7: a message view shows no source label and no table", () => {
    const container = renderList({ kind: "message", text: "x" });
    expect(screen.queryByText(LIVE_LABEL)).toBeNull();
    expect(screen.queryByText(RECORDED_LABEL_PREFIX, { exact: false })).toBeNull();
    expect(container.querySelector("table")).toBeNull();
  });

  it("Requirement 4 criterion 7: a live view with no violations shows the empty text and no table rows", () => {
    const container = renderList({ kind: "live", violations: [], replayed: null });
    expect(screen.getByText(NO_VIOLATIONS).localName).toBe("p");
    expect(container.querySelectorAll("tbody tr")).toHaveLength(0);
  });

  it("Requirement 4 criterion 5: a violation without c_line shows not from C in its c_line cell", () => {
    const container = renderList({ kind: "live", violations: [WITHOUT_LINE], replayed: null });
    expect(container.querySelectorAll("tbody tr")).toHaveLength(1);
    expect(columnTexts(container, "c_line")).toStrictEqual([NOT_FROM_C]);
  });

  it("Requirement 4 criterion 4: a violation with c_line 7 shows 7 in its c_line cell and not not from C", () => {
    const container = renderList({ kind: "live", violations: [WITH_LINE], replayed: null });
    expect(columnTexts(container, "c_line")).toStrictEqual(["7"]);
    expect(columnTexts(container, "c_line")).not.toContain(NOT_FROM_C);
  });

  it("Requirement 4 criterion 2: rows for bits 0, 2, 3 appear in array order", () => {
    const container = renderList({
      kind: "live",
      violations: [bitViolation(0), bitViolation(2), bitViolation(3)],
      replayed: null,
    });
    expect(columnTexts(container, "bit")).toStrictEqual(["0", "2", "3"]);
  });

  it("Requirement 4 criterion 2: reversed input for bits 3, 2, 0 appears in the reversed order, not sorted", () => {
    const container = renderList({
      kind: "live",
      violations: [bitViolation(3), bitViolation(2), bitViolation(0)],
      replayed: null,
    });
    expect(columnTexts(container, "bit")).toStrictEqual(["3", "2", "0"]);
  });

  it("Requirement 4 criterion 3: the header row lists register, bit, intended, actual, cycle, c_line in that order", () => {
    const container = renderList({ kind: "live", violations: [WITH_LINE], replayed: null });
    expect(headerTexts(container)).toStrictEqual(["register", "bit", "intended", "actual", "cycle", "c_line"]);
  });
});
