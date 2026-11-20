import { describe, it, expect } from "vitest";
import {
  parseErrorResponse,
  parseReplayedState,
  parseReportText,
  parseRunBody,
  parseSnapshot,
  parseSnippetList,
} from "../lib/reader";

const DEMO_ORDER = [
  "ISR_RMW_SNIPPET",
  "ISR_DIRECT_SNIPPET",
  "RDR_DOUBLE_READ_SNIPPET",
  "RDR_SINGLE_READ_SNIPPET",
];

const SOURCE_TEXT = "int main(void) {}";
const CREATED_UTC = "2024-05-01T12:00:00Z";

const ISR_VIOLATION = { register: "UART_ISR", bit: 3, intended: 0, actual: 1, cycle: 5 };

function snapshotRecord(name: string): Record<string, unknown> {
  return { name, source: SOURCE_TEXT, report: "[]", replayed_state: null };
}

function snapshotText(records: unknown[], createdUtc: string = CREATED_UTC): string {
  return JSON.stringify({ created_utc: createdUtc, records });
}

function snippetList(): { name: string; source: string }[] {
  return DEMO_ORDER.map((name) => ({ name, source: SOURCE_TEXT }));
}

describe("parseReportText", () => {
  it("accepts a valid one-element array with c_line absent and omits the key", () => {
    expect(parseReportText(JSON.stringify([ISR_VIOLATION]))).toStrictEqual({
      ok: true,
      value: [ISR_VIOLATION],
    });
  });

  it("returns c_line when it is present and at least 1", () => {
    expect(parseReportText(JSON.stringify([{ ...ISR_VIOLATION, c_line: 7 }]))).toStrictEqual({
      ok: true,
      value: [{ ...ISR_VIOLATION, c_line: 7 }],
    });
  });

  it("rejects c_line 0", () => {
    expect(parseReportText(JSON.stringify([{ ...ISR_VIOLATION, c_line: 0 }]))).toStrictEqual({ ok: false });
  });

  it("rejects bit 8 for UART_RDR", () => {
    const text = JSON.stringify([{ register: "UART_RDR", bit: 8, intended: 0, actual: 1, cycle: 5 }]);
    expect(parseReportText(text)).toStrictEqual({ ok: false });
  });

  it("rejects intended 2", () => {
    expect(parseReportText(JSON.stringify([{ ...ISR_VIOLATION, intended: 2 }]))).toStrictEqual({ ok: false });
  });

  it("rejects an element with an extra key", () => {
    expect(parseReportText(JSON.stringify([{ ...ISR_VIOLATION, extra: 1 }]))).toStrictEqual({ ok: false });
  });

  it("rejects bit 4 for UART_ISR", () => {
    expect(parseReportText(JSON.stringify([{ ...ISR_VIOLATION, bit: 4 }]))).toStrictEqual({ ok: false });
  });

  it("rejects a JSON object that is not an array", () => {
    expect(parseReportText(JSON.stringify({ violations: [ISR_VIOLATION] }))).toStrictEqual({ ok: false });
  });

  it("accepts an empty array and returns an empty list", () => {
    expect(parseReportText("[]")).toStrictEqual({ ok: true, value: [] });
  });
});

describe("parseReplayedState", () => {
  it("accepts null and returns null", () => {
    expect(parseReplayedState(null)).toStrictEqual({ ok: true, value: null });
  });

  it("rejects UART_ISR pre 16", () => {
    expect(parseReplayedState({ register: "UART_ISR", pre: 16, post: 0 })).toStrictEqual({ ok: false });
  });

  it("accepts a UART_RDR state with pre 255", () => {
    expect(parseReplayedState({ register: "UART_RDR", pre: 255, post: 0 })).toStrictEqual({
      ok: true,
      value: { register: "UART_RDR", pre: 255, post: 0 },
    });
  });

  it("rejects an object with an extra key", () => {
    expect(parseReplayedState({ register: "UART_RDR", pre: 1, post: 2, extra: 3 })).toStrictEqual({ ok: false });
  });

  it("rejects an object with a missing key", () => {
    expect(parseReplayedState({ register: "UART_RDR", pre: 1 })).toStrictEqual({ ok: false });
  });
});

describe("parseRunBody", () => {
  it("accepts a body with exactly the keys report and replayed_state", () => {
    const body = {
      report: JSON.stringify([ISR_VIOLATION]),
      replayed_state: { register: "UART_ISR", pre: 0, post: 4 },
    };
    expect(parseRunBody(JSON.stringify(body))).toStrictEqual({
      ok: true,
      value: {
        violations: [ISR_VIOLATION],
        replayed: { register: "UART_ISR", pre: 0, post: 4 },
      },
    });
  });

  it("rejects a body without the replayed_state key", () => {
    expect(parseRunBody(JSON.stringify({ report: "[]" }))).toStrictEqual({ ok: false });
  });

  it("rejects a body with an extra key", () => {
    expect(parseRunBody(JSON.stringify({ report: "[]", replayed_state: null, extra: 1 }))).toStrictEqual({
      ok: false,
    });
  });
});

describe("parseSnapshot", () => {
  it("accepts four records in DEMO order and returns them", () => {
    const text = snapshotText(DEMO_ORDER.map(snapshotRecord));
    expect(parseSnapshot(text)).toStrictEqual({
      ok: true,
      value: {
        createdUtc: CREATED_UTC,
        records: DEMO_ORDER.map((name) => ({ name, source: SOURCE_TEXT, violations: [], replayed: null })),
      },
    });
  });

  it("rejects records that are out of DEMO order", () => {
    const text = snapshotText(DEMO_ORDER.map(snapshotRecord).reverse());
    expect(parseSnapshot(text)).toStrictEqual({ ok: false });
  });

  it("rejects created_utc without the trailing Z", () => {
    const text = snapshotText(DEMO_ORDER.map(snapshotRecord), "2024-05-01T12:00:00");
    expect(parseSnapshot(text)).toStrictEqual({ ok: false });
  });

  it("rejects a snapshot whose record has a report that is an object", () => {
    const records = [
      snapshotRecord("ISR_RMW_SNIPPET"),
      { ...snapshotRecord("ISR_DIRECT_SNIPPET"), report: "{}" },
      snapshotRecord("RDR_DOUBLE_READ_SNIPPET"),
      snapshotRecord("RDR_SINGLE_READ_SNIPPET"),
    ];
    expect(parseSnapshot(snapshotText(records))).toStrictEqual({ ok: false });
  });
});

describe("parseSnippetList", () => {
  it("accepts four snippets in DEMO order", () => {
    expect(parseSnippetList(JSON.stringify(snippetList()))).toStrictEqual({
      ok: true,
      value: snippetList(),
    });
  });

  it("rejects snippets that are out of DEMO order", () => {
    expect(parseSnippetList(JSON.stringify(snippetList().reverse()))).toStrictEqual({ ok: false });
  });
});

describe("parseErrorResponse", () => {
  it("maps 409 with a busy body to busy", () => {
    expect(parseErrorResponse(409, JSON.stringify({ error: "busy" }))).toStrictEqual({ kind: "busy" });
  });

  it("maps 409 with another body to cannot_read", () => {
    expect(parseErrorResponse(409, JSON.stringify({ error: "other" }))).toStrictEqual({ kind: "cannot_read" });
  });

  it("maps 504 with a timeout body to timeout", () => {
    expect(parseErrorResponse(504, JSON.stringify({ error: "timeout" }))).toStrictEqual({ kind: "timeout" });
  });

  it("maps 504 with another body to cannot_read", () => {
    expect(parseErrorResponse(504, JSON.stringify({ error: "other" }))).toStrictEqual({ kind: "cannot_read" });
  });

  it("maps 400 with a too_large body to too_large", () => {
    expect(parseErrorResponse(400, JSON.stringify({ error: "too_large" }))).toStrictEqual({ kind: "too_large" });
  });

  it("maps 422 with a valid parser_error body to the line and message", () => {
    const text = JSON.stringify({ error: "parser_error", line: 3, message: "unknown token" });
    expect(parseErrorResponse(422, text)).toStrictEqual({
      kind: "parser_error",
      line: 3,
      message: "unknown token",
    });
  });

  it("maps 500 simulation_failed to its message with newlines replaced by spaces", () => {
    const text = JSON.stringify({ error: "simulation_failed", message: "first\nsecond\r\nthird" });
    expect(parseErrorResponse(500, text)).toStrictEqual({
      kind: "simulation_failed",
      message: "first second third",
    });
  });

  it("maps a non-JSON 409 body to cannot_read without throwing", () => {
    expect(parseErrorResponse(409, "busy")).toStrictEqual({ kind: "cannot_read" });
  });

  it("maps a non-JSON 504 body to cannot_read without throwing", () => {
    expect(parseErrorResponse(504, "timeout")).toStrictEqual({ kind: "cannot_read" });
  });

  it("maps a status outside the table to unexpected_status with that status", () => {
    expect(parseErrorResponse(418, JSON.stringify({ error: "teapot" }))).toStrictEqual({
      kind: "unexpected_status",
      status: 418,
    });
  });
});

describe("reader functions never throw", () => {
  it("parseReportText returns ok false for non-JSON text and for a non-string", () => {
    expect(parseReportText("not json")).toStrictEqual({ ok: false });
    expect(parseReportText(42 as unknown as string)).toStrictEqual({ ok: false });
  });

  it("parseReplayedState returns ok false for a string and for undefined", () => {
    expect(parseReplayedState("{not json")).toStrictEqual({ ok: false });
    expect(parseReplayedState(undefined)).toStrictEqual({ ok: false });
  });

  it("parseRunBody returns ok false for non-JSON text and for a non-string", () => {
    expect(parseRunBody("not json")).toStrictEqual({ ok: false });
    expect(parseRunBody(42 as unknown as string)).toStrictEqual({ ok: false });
  });

  it("parseSnapshot returns ok false for non-JSON text and for null", () => {
    expect(parseSnapshot("{")).toStrictEqual({ ok: false });
    expect(parseSnapshot(null as unknown as string)).toStrictEqual({ ok: false });
  });

  it("parseSnippetList returns ok false for non-JSON text and for an object", () => {
    expect(parseSnippetList("[")).toStrictEqual({ ok: false });
    expect(parseSnippetList({} as unknown as string)).toStrictEqual({ ok: false });
  });

  it("parseErrorResponse returns cannot_read for non-JSON text and for a non-string", () => {
    expect(parseErrorResponse(500, "{")).toStrictEqual({ kind: "cannot_read" });
    expect(parseErrorResponse(422, 42 as unknown as string)).toStrictEqual({ kind: "cannot_read" });
  });
});
