import { describe, it, expect } from "vitest";
import { MAX_BYTES, MAX_LINES } from "../lib/config";
import { countLines, demoNameFor, isTooLarge, runBody, utf8ByteLength } from "../lib/snippetState";

const ISR_RMW_SOURCE = "void h(void) {\n UART_ISR = (1U << TX_DONE);\n}\n";
const ISR_DIRECT_SOURCE = "void h(void) {\n UART_ISR = (1U << PARITY_ERR);\n}\n";
const SOURCES: Record<string, string> = {
  ISR_RMW_SNIPPET: ISR_RMW_SOURCE,
  ISR_DIRECT_SNIPPET: ISR_DIRECT_SOURCE,
};

describe("countLines", () => {
  // The same inputs and results as tests/test_count_lines.py.
  it.each<[string, string, number]>([
    ["empty string", "", 0],
    ["one character", "x", 1],
    ["one LF at the end", "x\n", 1],
    ["CRLF at the end", "x\r\n", 1],
    ["lone CR at the end", "x\r", 1],
    ["two LF at the end", "x\n\n", 2],
    ["U+2028 between two words", "a\u2028b", 1],
    ["VT between two words", "a\u000bb", 1],
    ["FF between two words", "a\u000cb", 1],
    ["NEL between two words", "a\u0085b", 1],
  ])("%s gives %i", (_label, text, expected) => {
    expect(countLines(text)).toBe(expected);
  });

  it("counts the handler with a U+2028 between two words as 1 line", () => {
    expect(countLines("void h(void) {\u2028 UART_ISR = (1U << TX_DONE);\u2028}")).toBe(1);
  });
});

describe("size limit", () => {
  it("uses the limits 200 lines and 8192 bytes from config", () => {
    expect(MAX_LINES).toBe(200);
    expect(MAX_BYTES).toBe(8192);
  });

  it("200 lines counts as 200 and is not too large", () => {
    const text = new Array<string>(200).fill("x").join("\n");
    expect(countLines(text)).toBe(200);
    expect(isTooLarge(text)).toBe(false);
  });

  it("201 lines counts as 201 and is too large", () => {
    const text = new Array<string>(201).fill("x").join("\n");
    expect(countLines(text)).toBe(201);
    expect(isTooLarge(text)).toBe(true);
  });

  it("8192 ASCII bytes is not too large", () => {
    const text = "a".repeat(8192);
    expect(utf8ByteLength(text)).toBe(8192);
    expect(isTooLarge(text)).toBe(false);
  });

  it("8193 ASCII bytes is too large", () => {
    const text = "a".repeat(8193);
    expect(utf8ByteLength(text)).toBe(8193);
    expect(isTooLarge(text)).toBe(true);
  });

  it("4096 two-byte characters is 8192 bytes and not too large", () => {
    const text = "\u00e9".repeat(4096);
    expect(utf8ByteLength(text)).toBe(8192);
    expect(isTooLarge(text)).toBe(false);
  });

  it("4097 two-byte characters is 8194 bytes and too large", () => {
    const text = "\u00e9".repeat(4097);
    expect(utf8ByteLength(text)).toBe(8194);
    expect(isTooLarge(text)).toBe(true);
  });

  it("a handler with a U+2028 between two words is not too large", () => {
    const text = "void h(void) {\u2028 UART_ISR = (1U << TX_DONE);\u2028}";
    expect(countLines(text)).toBe(1);
    expect(isTooLarge(text)).toBe(false);
  });
});

describe("demoNameFor", () => {
  it("returns the selected name when the code equals its source exactly", () => {
    expect(demoNameFor(ISR_RMW_SOURCE, "ISR_RMW_SNIPPET", SOURCES)).toBe("ISR_RMW_SNIPPET");
  });

  it("returns null when the code equals another demo's source", () => {
    expect(demoNameFor(ISR_DIRECT_SOURCE, "ISR_RMW_SNIPPET", SOURCES)).toBeNull();
  });

  it("returns null after one extra trailing space", () => {
    expect(demoNameFor(ISR_RMW_SOURCE + " ", "ISR_RMW_SNIPPET", SOURCES)).toBeNull();
  });

  it("returns null after one changed letter", () => {
    expect(demoNameFor(ISR_RMW_SOURCE.replace("TX_DONE", "TX_DONF"), "ISR_RMW_SNIPPET", SOURCES)).toBeNull();
  });

  it("returns null when the selected name is not in the sources", () => {
    expect(demoNameFor(ISR_RMW_SOURCE, "NO_SUCH_SNIPPET", SOURCES)).toBeNull();
  });

  it("returns null when the source map is empty", () => {
    expect(demoNameFor(ISR_RMW_SOURCE, "ISR_RMW_SNIPPET", {})).toBeNull();
  });
});

describe("runBody", () => {
  it("returns the snippet name when the demo name is set", () => {
    expect(runBody(ISR_RMW_SOURCE, "ISR_RMW_SNIPPET")).toStrictEqual({ snippet: "ISR_RMW_SNIPPET" });
  });

  it("returns the code text in c_source when the demo name is null", () => {
    const userCode = "void h(void) {\n UART_ISR = (1U << OVERRUN_ERR);\n}\n";
    expect(runBody(userCode, null)).toStrictEqual({ c_source: userCode });
  });
});
