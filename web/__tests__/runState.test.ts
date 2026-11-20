import { describe, it, expect } from "vitest";
import {
  BUSY,
  CANNOT_READ,
  NO_RESPONSE,
  REJECTED,
  SIMULATION_FAILED_PREFIX,
  TIMEOUT,
  TOO_LARGE,
  UNEXPECTED_STATUS_PREFIX,
} from "../lib/messages";
import { outcomeShown, routeRun, startRun, userTooLargeShown } from "../lib/runState";

describe("startRun", () => {
  it("returns pending true and an empty shown state", () => {
    expect(startRun()).toStrictEqual({ pending: true, shown: { kind: "empty" } });
  });
});

describe("routeRun", () => {
  it("sends an unreachable demo run to the recorded path", () => {
    expect(routeRun({ kind: "unreachable" }, "demo")).toBe("recorded");
  });

  it("returns unreachable_user for an unreachable user run", () => {
    expect(routeRun({ kind: "unreachable" }, "user")).toBe("unreachable_user");
  });

  it("disables run control for a demo run while the backend state is unknown", () => {
    expect(routeRun({ kind: "unknown" }, "demo")).toBe("disabled");
  });

  it("disables run control for a user run while the backend state is unknown", () => {
    expect(routeRun({ kind: "unknown" }, "user")).toBe("disabled");
  });

  it("sends a demo run when the backend is reachable", () => {
    expect(routeRun({ kind: "reachable", busy: false }, "demo")).toBe("send");
  });

  it("sends a user run when the backend is reachable", () => {
    expect(routeRun({ kind: "reachable", busy: false }, "user")).toBe("send");
  });
});

describe("userTooLargeShown", () => {
  it("returns the too-large message for 201 lines", () => {
    const code = Array(201).fill("x").join("\n");
    expect(userTooLargeShown(code)).toStrictEqual({ kind: "message", text: TOO_LARGE });
  });

  it("returns null for 200 lines", () => {
    const code = Array(200).fill("x").join("\n");
    expect(userTooLargeShown(code)).toBeNull();
  });

  it("returns the too-large message for 8193 UTF-8 bytes", () => {
    expect(userTooLargeShown("a".repeat(8193))).toStrictEqual({ kind: "message", text: TOO_LARGE });
  });

  it("returns null for 200 ordinary lines under the byte limit", () => {
    const code = Array(200).fill("UART_ISR = (1U << TX_DONE);").join("\n");
    expect(userTooLargeShown(code)).toBeNull();
  });
});

describe("outcomeShown", () => {
  it("shows the no-response message for no_response and never a recorded kind", () => {
    const shown = outcomeShown({ kind: "no_response" });
    expect(shown).toStrictEqual({ kind: "message", text: NO_RESPONSE });
    expect(shown.kind).not.toBe("recorded");
  });

  it("shows live results for a 200 with a valid body", () => {
    const shown = outcomeShown({ kind: "response", status: 200, text: '{"report": "[]", "replayed_state": null}' });
    expect(shown).toStrictEqual({ kind: "live", violations: [], replayed: null });
  });

  it("shows the cannot-read message for a 200 with an invalid body", () => {
    const shown = outcomeShown({ kind: "response", status: 200, text: "not json" });
    expect(shown).toStrictEqual({ kind: "message", text: CANNOT_READ });
  });

  it("shows the too-large message for 400 too_large", () => {
    const shown = outcomeShown({ kind: "response", status: 400, text: '{"error":"too_large"}' });
    expect(shown).toStrictEqual({ kind: "message", text: TOO_LARGE });
  });

  it("shows the rejected message for 400 invalid_request", () => {
    const shown = outcomeShown({ kind: "response", status: 400, text: '{"error":"invalid_request"}' });
    expect(shown).toStrictEqual({ kind: "message", text: REJECTED });
  });

  it("shows the rejected message for a 400 with another body", () => {
    const shown = outcomeShown({ kind: "response", status: 400, text: '{"error":"x"}' });
    expect(shown).toStrictEqual({ kind: "message", text: REJECTED });
  });

  it("shows the busy message for 409 busy", () => {
    const shown = outcomeShown({ kind: "response", status: 409, text: '{"error":"busy"}' });
    expect(shown).toStrictEqual({ kind: "message", text: BUSY });
  });

  it("shows the cannot-read message for a 409 with another body", () => {
    const shown = outcomeShown({ kind: "response", status: 409, text: '{"error":"x"}' });
    expect(shown).toStrictEqual({ kind: "message", text: CANNOT_READ });
  });

  it("shows the parser error as Line N and the message for 422 parser_error", () => {
    const shown = outcomeShown({
      kind: "response",
      status: 422,
      text: '{"error":"parser_error","line":2,"message":"loops are not supported"}',
    });
    expect(shown).toStrictEqual({ kind: "message", text: "Line 2: loops are not supported" });
  });

  it("shows the cannot-read message for a 422 with another body", () => {
    const shown = outcomeShown({ kind: "response", status: 422, text: '{"error":"x"}' });
    expect(shown).toStrictEqual({ kind: "message", text: CANNOT_READ });
  });

  it("shows the simulation failure with its message for 500 simulation_failed", () => {
    const shown = outcomeShown({ kind: "response", status: 500, text: '{"error":"simulation_failed","message":"bad"}' });
    expect(shown).toStrictEqual({ kind: "message", text: SIMULATION_FAILED_PREFIX + "bad" });
  });

  it("shows the cannot-read message for a 500 with another body", () => {
    const shown = outcomeShown({ kind: "response", status: 500, text: '{"error":"x"}' });
    expect(shown).toStrictEqual({ kind: "message", text: CANNOT_READ });
  });

  it("shows the timeout message for 504 timeout", () => {
    const shown = outcomeShown({ kind: "response", status: 504, text: '{"error":"timeout"}' });
    expect(shown).toStrictEqual({ kind: "message", text: TIMEOUT });
  });

  it("shows the cannot-read message for a 504 with another body", () => {
    const shown = outcomeShown({ kind: "response", status: 504, text: '{"error":"x"}' });
    expect(shown).toStrictEqual({ kind: "message", text: CANNOT_READ });
  });

  it("shows the unexpected-status message with the code for an unlisted status", () => {
    const shown = outcomeShown({ kind: "response", status: 418, text: '{"error":"x"}' });
    expect(shown).toStrictEqual({ kind: "message", text: UNEXPECTED_STATUS_PREFIX + "418" });
  });

  describe("error responses", () => {
    it.each<[string, number, string, string]>([
      ["400 too_large", 400, '{"error":"too_large"}', TOO_LARGE],
      ["400 invalid_request", 400, '{"error":"invalid_request"}', REJECTED],
      ["400 other body", 400, '{"error":"x"}', REJECTED],
      ["409 busy", 409, '{"error":"busy"}', BUSY],
      ["409 other body", 409, '{"error":"x"}', CANNOT_READ],
      [
        "422 parser_error",
        422,
        '{"error":"parser_error","line":2,"message":"loops are not supported"}',
        "Line 2: loops are not supported",
      ],
      ["422 other body", 422, '{"error":"x"}', CANNOT_READ],
      ["500 simulation_failed", 500, '{"error":"simulation_failed","message":"bad"}', SIMULATION_FAILED_PREFIX + "bad"],
      ["500 other body", 500, '{"error":"x"}', CANNOT_READ],
      ["504 timeout", 504, '{"error":"timeout"}', TIMEOUT],
      ["504 other body", 504, '{"error":"x"}', CANNOT_READ],
      ["418 unexpected status", 418, '{"error":"x"}', UNEXPECTED_STATUS_PREFIX + "418"],
    ])("%s gives a message and never a recorded kind", (_label, status, text, expectedText) => {
      const shown = outcomeShown({ kind: "response", status, text });
      expect(shown.kind).not.toBe("recorded");
      expect(shown.kind).toBe("message");
      expect(shown).toStrictEqual({ kind: "message", text: expectedText });
    });
  });
});
