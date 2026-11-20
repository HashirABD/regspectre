import type { DemoSnippet, Register, Replayed, Result, Snapshot, SnapshotRecord, Violation } from "./types";

// Demo_Snippet names in DEMO order. Snippet lists and Snapshot records must use this order.
export const DEMO_NAMES: readonly string[] = [
  "ISR_RMW_SNIPPET",
  "ISR_DIRECT_SNIPPET",
  "RDR_DOUBLE_READ_SNIPPET",
  "RDR_SINGLE_READ_SNIPPET",
];

const ISR_WIDTH = 4;
const RDR_WIDTH = 8;
const MAX_MESSAGE_CHARS = 500;
const CREATED_UTC_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;

const REPORT_REQUIRED_KEYS = ["register", "bit", "intended", "actual", "cycle"];
const REPORT_OPTIONAL_KEY = "c_line";
const REPLAYED_KEYS = ["register", "pre", "post"];
const RUN_BODY_KEYS = ["report", "replayed_state"];
const SNAPSHOT_KEYS = ["created_utc", "records"];
const SNAPSHOT_RECORD_KEYS = ["name", "source", "report", "replayed_state"];
const SNIPPET_KEYS = ["name", "source"];

// The reply for a run response that is not a 200. Mapped from design 6.5.
export type ErrorReply =
  | { kind: "busy" }
  | { kind: "timeout" }
  | { kind: "too_large" }
  | { kind: "rejected" }
  | { kind: "parser_error"; line: number; message: string }
  | { kind: "simulation_failed"; message: string }
  | { kind: "unexpected_status"; status: number }
  | { kind: "cannot_read" };

function parseJsonText(text: unknown): Result<unknown> {
  if (typeof text !== "string") {
    return { ok: false };
  }
  try {
    const value: unknown = JSON.parse(text);
    return { ok: true, value };
  } catch {
    return { ok: false };
  }
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

// True when the object has exactly the given keys and no others.
function hasExactKeys(obj: Record<string, unknown>, keys: readonly string[]): boolean {
  const ownKeys = Object.keys(obj);
  return ownKeys.length === keys.length && keys.every((key) => Object.prototype.hasOwnProperty.call(obj, key));
}

function isExactObject(value: unknown, keys: readonly string[]): value is Record<string, unknown> {
  return isPlainObject(value) && hasExactKeys(value, keys);
}

function isInteger(value: unknown, min: number, max: number): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= min && value <= max;
}

function isRegister(value: unknown): value is Register {
  return value === "UART_ISR" || value === "UART_RDR";
}

function widthOf(register: Register): number {
  return register === "UART_ISR" ? ISR_WIDTH : RDR_WIDTH;
}

// Backend text is shown as plain text only. Newlines become spaces, and the text is cut to 500 characters.
function oneLineText(text: string): string {
  const flat = text.replace(/\r\n|\r|\n/g, " ");
  return Array.from(flat).slice(0, MAX_MESSAGE_CHARS).join("");
}

function parseViolation(value: unknown): Violation | null {
  const hasCLine = isPlainObject(value) && Object.prototype.hasOwnProperty.call(value, REPORT_OPTIONAL_KEY);
  const keys = hasCLine ? [...REPORT_REQUIRED_KEYS, REPORT_OPTIONAL_KEY] : REPORT_REQUIRED_KEYS;
  if (!isExactObject(value, keys)) {
    return null;
  }
  const { register, bit, intended, actual, cycle } = value;
  if (!isRegister(register)) {
    return null;
  }
  if (!isInteger(bit, 0, widthOf(register) - 1)) {
    return null;
  }
  if (!isInteger(intended, 0, 1) || !isInteger(actual, 0, 1)) {
    return null;
  }
  if (!isInteger(cycle, 0, Number.POSITIVE_INFINITY)) {
    return null;
  }
  const violation: Violation = { register, bit, intended, actual, cycle };
  if (hasCLine) {
    const cLine = value[REPORT_OPTIONAL_KEY];
    if (!isInteger(cLine, 1, Number.POSITIVE_INFINITY)) {
      return null;
    }
    violation.c_line = cLine;
  }
  return violation;
}

export function parseReportText(text: string): Result<Violation[]> {
  const parsed = parseJsonText(text);
  if (!parsed.ok) {
    return { ok: false };
  }
  const elements = parsed.value;
  if (!Array.isArray(elements)) {
    return { ok: false };
  }
  const violations: Violation[] = [];
  for (const element of elements) {
    const violation = parseViolation(element);
    if (violation === null) {
      return { ok: false };
    }
    violations.push(violation);
  }
  return { ok: true, value: violations };
}

export function parseReplayedState(value: unknown): Result<Replayed | null> {
  if (value === null) {
    return { ok: true, value: null };
  }
  if (!isExactObject(value, REPLAYED_KEYS)) {
    return { ok: false };
  }
  const { register, pre, post } = value;
  if (!isRegister(register)) {
    return { ok: false };
  }
  const max = 2 ** widthOf(register) - 1;
  if (!isInteger(pre, 0, max) || !isInteger(post, 0, max)) {
    return { ok: false };
  }
  return { ok: true, value: { register, pre, post } };
}

export function parseRunBody(text: string): Result<{ violations: Violation[]; replayed: Replayed | null }> {
  const parsed = parseJsonText(text);
  if (!parsed.ok) {
    return { ok: false };
  }
  const body = parsed.value;
  if (!isExactObject(body, RUN_BODY_KEYS)) {
    return { ok: false };
  }
  const { report, replayed_state } = body;
  if (typeof report !== "string") {
    return { ok: false };
  }
  const violations = parseReportText(report);
  if (!violations.ok) {
    return { ok: false };
  }
  const replayed = parseReplayedState(replayed_state);
  if (!replayed.ok) {
    return { ok: false };
  }
  return { ok: true, value: { violations: violations.value, replayed: replayed.value } };
}

function parseSnapshotRecord(value: unknown, expectedName: string): Result<SnapshotRecord> {
  if (!isExactObject(value, SNAPSHOT_RECORD_KEYS)) {
    return { ok: false };
  }
  const { name, source, report, replayed_state } = value;
  if (typeof name !== "string" || name !== expectedName) {
    return { ok: false };
  }
  if (typeof source !== "string" || typeof report !== "string") {
    return { ok: false };
  }
  const violations = parseReportText(report);
  if (!violations.ok) {
    return { ok: false };
  }
  const replayed = parseReplayedState(replayed_state);
  if (!replayed.ok) {
    return { ok: false };
  }
  return { ok: true, value: { name, source, violations: violations.value, replayed: replayed.value } };
}

export function parseSnapshot(text: string): Result<Snapshot> {
  const parsed = parseJsonText(text);
  if (!parsed.ok) {
    return { ok: false };
  }
  const body = parsed.value;
  if (!isExactObject(body, SNAPSHOT_KEYS)) {
    return { ok: false };
  }
  const { created_utc, records } = body;
  if (typeof created_utc !== "string" || !CREATED_UTC_PATTERN.test(created_utc)) {
    return { ok: false };
  }
  if (!Array.isArray(records) || records.length !== DEMO_NAMES.length) {
    return { ok: false };
  }
  const parsedRecords: SnapshotRecord[] = [];
  for (let i = 0; i < DEMO_NAMES.length; i++) {
    const record = parseSnapshotRecord(records[i], DEMO_NAMES[i]);
    if (!record.ok) {
      return { ok: false };
    }
    parsedRecords.push(record.value);
  }
  return { ok: true, value: { createdUtc: created_utc, records: parsedRecords } };
}

export function parseSnippetList(text: string): Result<DemoSnippet[]> {
  const parsed = parseJsonText(text);
  if (!parsed.ok) {
    return { ok: false };
  }
  const list = parsed.value;
  if (!Array.isArray(list) || list.length !== DEMO_NAMES.length) {
    return { ok: false };
  }
  const snippets: DemoSnippet[] = [];
  for (let i = 0; i < DEMO_NAMES.length; i++) {
    const item: unknown = list[i];
    if (!isExactObject(item, SNIPPET_KEYS)) {
      return { ok: false };
    }
    const { name, source } = item;
    if (typeof name !== "string" || name !== DEMO_NAMES[i] || typeof source !== "string") {
      return { ok: false };
    }
    snippets.push({ name, source });
  }
  return { ok: true, value: snippets };
}

function parserErrorReply(body: unknown): ErrorReply {
  if (!isExactObject(body, ["error", "line", "message"]) || body.error !== "parser_error") {
    return { kind: "cannot_read" };
  }
  const { line, message } = body;
  if (!isInteger(line, 1, Number.POSITIVE_INFINITY) || typeof message !== "string") {
    return { kind: "cannot_read" };
  }
  return { kind: "parser_error", line, message: oneLineText(message) };
}

function simulationFailedReply(body: unknown): ErrorReply {
  if (!isExactObject(body, ["error", "message"]) || body.error !== "simulation_failed") {
    return { kind: "cannot_read" };
  }
  const { message } = body;
  if (typeof message !== "string") {
    return { kind: "cannot_read" };
  }
  return { kind: "simulation_failed", message: oneLineText(message) };
}

// Maps a non-200 run response to a reply, following design 6.5.
export function parseErrorResponse(status: number, text: string): ErrorReply {
  const parsed = parseJsonText(text);
  const body: unknown = parsed.ok ? parsed.value : undefined;
  switch (status) {
    case 400:
      return isExactObject(body, ["error"]) && body.error === "too_large"
        ? { kind: "too_large" }
        : { kind: "rejected" };
    case 409:
      return isExactObject(body, ["error"]) && body.error === "busy"
        ? { kind: "busy" }
        : { kind: "cannot_read" };
    case 422:
      return parserErrorReply(body);
    case 500:
      return simulationFailedReply(body);
    case 504:
      return isExactObject(body, ["error"]) && body.error === "timeout"
        ? { kind: "timeout" }
        : { kind: "cannot_read" };
    case 200:
      // A 200 is a success response. It is read by parseRunBody, not here.
      return { kind: "cannot_read" };
    default:
      return { kind: "unexpected_status", status };
  }
}
