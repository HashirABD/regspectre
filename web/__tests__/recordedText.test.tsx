import { describe, it, expect, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { Disclaimers } from "../components/Disclaimers";
import { Message } from "../components/Message";
import { RegisterArray } from "../components/RegisterArray";
import { ViolationList } from "../components/ViolationList";
import {
  DISCLAIMER_1,
  DISCLAIMER_2,
  DISCLAIMER_3,
  DISCLAIMER_4,
  DISCLAIMER_5,
  LIVE_LABEL,
  RECORDED_LABEL_PREFIX,
  REPLAYED_NOTE_1,
  REPLAYED_NOTE_2,
} from "../lib/messages";
import { buildRegisterCells, type Shown } from "../lib/registerCells";
import type { Replayed, Violation } from "../lib/types";

const LIVE_WORD = /live/i;
const CREATED_UTC = "2026-11-15T12:00:00Z";
const REPLAYED: Replayed = { register: "UART_ISR", pre: 9, post: 0 };
const VIOLATION: Violation = { register: "UART_ISR", bit: 3, intended: 1, actual: 0, cycle: 4, c_line: 6 };
const RECORDED: Shown = { kind: "recorded", createdUtc: CREATED_UTC, violations: [VIOLATION], replayed: REPLAYED };
const LIVE: Shown = { kind: "live", violations: [VIOLATION], replayed: REPLAYED };
const NOTHING = (): void => undefined;

// The five disclaimers and the two replayed notes, as the page renders them.
const DISCLAIMER_TEXTS = [
  DISCLAIMER_1,
  DISCLAIMER_2,
  DISCLAIMER_3,
  DISCLAIMER_4,
  DISCLAIMER_5,
  REPLAYED_NOTE_1,
  REPLAYED_NOTE_2,
];

afterEach(() => {
  cleanup();
});

// Renders the parts of the page that show results, inside one div. Returns that div.
function renderView(shown: Shown): HTMLElement {
  const { container } = render(
    <div>
      <ViolationList shown={shown} />
      <Disclaimers showReplayedNotes={true} />
      <RegisterArray register="UART_ISR" onRegisterChange={NOTHING} cells={buildRegisterCells("UART_ISR", shown)} />
      <Message text={null} />
    </div>
  );
  return container;
}

// The text of every text node under root, in document order.
function textNodes(root: Node): string[] {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const texts: string[] = [];
  let node: Node | null = walker.nextNode();
  while (node !== null) {
    texts.push(node.textContent ?? "");
    node = walker.nextNode();
  }
  return texts;
}

describe("recorded text", () => {
  it("Requirement 1 criterion 6: the recorded label is RECORDED_LABEL_PREFIX followed by createdUtc", () => {
    renderView(RECORDED);
    expect(screen.getByText(RECORDED_LABEL_PREFIX + CREATED_UTC).localName).toBe("p");
  });

  it("Requirement 8 criterion 13: no text node in the recorded view matches /live/i", () => {
    const container = renderView(RECORDED);
    const texts = textNodes(container);
    expect(texts.length).toBeGreaterThan(0);
    expect(texts.filter((text) => LIVE_WORD.test(text))).toStrictEqual([]);
  });

  it("Requirement 8 criterion 13: the text of the recorded view as a whole does not match /live/i", () => {
    const container = renderView(RECORDED);
    expect(container.textContent ?? "").not.toMatch(LIVE_WORD);
  });

  it("Requirement 10 criteria 1 to 5, 10 and 11, design 6.9: the disclaimers and replayed notes in the recorded view are rendered and do not match /live/i", () => {
    const container = renderView(RECORDED);
    const nodes = textNodes(container);
    expect(DISCLAIMER_TEXTS.filter((text) => nodes.includes(text))).toStrictEqual(DISCLAIMER_TEXTS);
    expect(DISCLAIMER_TEXTS.filter((text) => LIVE_WORD.test(text))).toStrictEqual([]);
  });

  it("positive control: the live view shows Live result, so the same text walk does find /live/i text", () => {
    const container = renderView(LIVE);
    const nodes = textNodes(container);
    expect(screen.getByText(LIVE_LABEL).localName).toBe("p");
    expect(nodes).toContain(LIVE_LABEL);
    expect(nodes.filter((text) => LIVE_WORD.test(text))).toStrictEqual([LIVE_LABEL]);
  });
});
