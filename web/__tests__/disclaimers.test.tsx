import { describe, it, expect, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { Disclaimers } from "../components/Disclaimers";
import {
  DISCLAIMER_1,
  DISCLAIMER_2,
  DISCLAIMER_3,
  DISCLAIMER_4,
  DISCLAIMER_5,
  REPLAYED_NOTE_1,
  REPLAYED_NOTE_2,
} from "../lib/messages";

const DISCLAIMERS = [DISCLAIMER_1, DISCLAIMER_2, DISCLAIMER_3, DISCLAIMER_4, DISCLAIMER_5];
const REPLAYED_NOTES = [REPLAYED_NOTE_1, REPLAYED_NOTE_2];

afterEach(() => {
  cleanup();
});

// Returns the tag names of the element and of each ancestor that hides it.
// A hiding element is a details element, an element with the hidden attribute, or an element with aria-hidden="true".
function hidingAncestors(element: HTMLElement): string[] {
  const found: string[] = [];
  let node: Element | null = element;
  while (node !== null) {
    if (node.localName === "details" || node.hasAttribute("hidden") || node.getAttribute("aria-hidden") === "true") {
      found.push(node.localName);
    }
    node = node.parentElement;
  }
  return found;
}

describe("Disclaimers", () => {
  it("Requirement 10 criteria 1 to 5: renders all five disclaimers when showReplayedNotes is false", () => {
    render(<Disclaimers showReplayedNotes={false} />);
    expect(DISCLAIMERS.map((text) => screen.getByText(text).localName)).toStrictEqual([
      "li",
      "li",
      "li",
      "li",
      "li",
    ]);
  });

  it("Requirement 10 criteria 1 to 5: renders all five disclaimers when showReplayedNotes is true", () => {
    render(<Disclaimers showReplayedNotes={true} />);
    expect(DISCLAIMERS.map((text) => screen.getByText(text).localName)).toStrictEqual([
      "li",
      "li",
      "li",
      "li",
      "li",
    ]);
  });

  it("Requirement 10 criteria 10 and 11: no replayed note is rendered when showReplayedNotes is false", () => {
    render(<Disclaimers showReplayedNotes={false} />);
    expect([screen.queryByText(REPLAYED_NOTE_1), screen.queryByText(REPLAYED_NOTE_2)]).toStrictEqual([null, null]);
  });

  it("Requirement 10 criteria 10 and 11: both replayed notes are rendered when showReplayedNotes is true", () => {
    render(<Disclaimers showReplayedNotes={true} />);
    expect(REPLAYED_NOTES.map((text) => screen.getByText(text).localName)).toStrictEqual(["li", "li"]);
  });

  it("Requirement 10 criterion 9: no disclaimer is inside a details, hidden, or aria-hidden element in either state", () => {
    for (const showReplayedNotes of [false, true]) {
      const { unmount } = render(<Disclaimers showReplayedNotes={showReplayedNotes} />);
      expect(DISCLAIMERS.map((text) => hidingAncestors(screen.getByText(text)))).toStrictEqual([[], [], [], [], []]);
      unmount();
    }
  });
});
