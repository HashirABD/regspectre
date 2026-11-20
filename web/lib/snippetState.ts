import { MAX_BYTES, MAX_LINES } from "./config";

// Line count for a User_Snippet (design 5.4). It splits on LF only, after
// folding CRLF and CR into LF, so U+2028 and the other separators do not count.
// The Python count_lines in backend/validation.py uses the same four steps.
export function countLines(text: string): number {
  if (text === "") {
    return 0;
  }
  let normalized = text.replace(/\r\n/g, "\n");
  normalized = normalized.replace(/\r/g, "\n");
  if (normalized.endsWith("\n")) {
    normalized = normalized.slice(0, -1);
  }
  return normalized.split("\n").length;
}

// Size of the text in UTF-8 bytes.
export function utf8ByteLength(text: string): number {
  return new TextEncoder().encode(text).length;
}

// True when the code pane text is over the client-side limit (design 6.5 and 6.7).
export function isTooLarge(code: string): boolean {
  return countLines(code) > MAX_LINES || utf8ByteLength(code) > MAX_BYTES;
}

// Returns the Demo_Snippet name when the code equals that snippet's source exactly.
// Otherwise returns null, which makes the text a User_Snippet (Requirement 2, criteria 5 and 7).
export function demoNameFor(
  code: string,
  selected: string,
  sources: Readonly<Record<string, string>>,
): string | null {
  const source = sources[selected];
  if (source === undefined) {
    return null;
  }
  return source === code ? selected : null;
}

// The run body: the name when the code is a Demo_Snippet, otherwise the code text (Requirement 2, criterion 6).
export function runBody(code: string, demoName: string | null): { snippet: string } | { c_source: string } {
  if (demoName !== null) {
    return { snippet: demoName };
  }
  return { c_source: code };
}
