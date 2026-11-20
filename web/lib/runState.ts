import { BUSY, CANNOT_READ, LINE_PREFIX, NO_RESPONSE, REJECTED, SIMULATION_FAILED_PREFIX, TIMEOUT, TOO_LARGE, UNEXPECTED_STATUS_PREFIX } from "./messages";
import type { ErrorReply } from "./reader";
import { parseErrorResponse, parseRunBody } from "./reader";
import type { Shown } from "./registerCells";
import { isTooLarge } from "./snippetState";

export type { Shown };

// Backend states from design 6.4.
export type BackendState = { kind: "unknown" } | { kind: "reachable"; busy: boolean } | { kind: "unreachable" };

// The result of POST /api/run (design 6.3), plus the no_response row of the 6.5 outcome table.
export type RunOutcome = { kind: "no_response" } | { kind: "response"; status: number; text: string };

// Starting a run clears the previous shown result (Requirement 9, criterion 7).
export function startRun(): { pending: true; shown: Shown } {
  return { pending: true, shown: { kind: "empty" } };
}

// Chooses what a run action does, following the request routing table in design 6.5.
export function routeRun(state: BackendState, source: "demo" | "user"): "send" | "recorded" | "unreachable_user" | "disabled" {
  if (state.kind === "unknown") {
    return "disabled";
  }
  if (state.kind === "reachable") {
    return "send";
  }
  return source === "demo" ? "recorded" : "unreachable_user";
}

// Client-side size check for a User_Snippet (Requirement 3, criterion 24). Returns null when the run may be sent.
export function userTooLargeShown(code: string): Shown | null {
  return isTooLarge(code) ? messageShown(TOO_LARGE) : null;
}

// Maps a run outcome to the Shown value in the design 6.5 outcome table.
// This never returns kind "recorded". Recorded output is built only on the unreachable path,
// where routeRun returns "recorded", and the page builds it. An error response never produces recorded output.
export function outcomeShown(outcome: RunOutcome): Shown {
  if (outcome.kind === "no_response") {
    return messageShown(NO_RESPONSE);
  }
  if (outcome.status === 200) {
    const parsed = parseRunBody(outcome.text);
    if (!parsed.ok) {
      return messageShown(CANNOT_READ);
    }
    return { kind: "live", violations: parsed.value.violations, replayed: parsed.value.replayed };
  }
  return errorShown(parseErrorResponse(outcome.status, outcome.text));
}

function messageShown(text: string): Shown {
  return { kind: "message", text };
}

function errorShown(reply: ErrorReply): Shown {
  switch (reply.kind) {
    case "busy":
      return messageShown(BUSY);
    case "timeout":
      return messageShown(TIMEOUT);
    case "too_large":
      return messageShown(TOO_LARGE);
    case "rejected":
      return messageShown(REJECTED);
    case "parser_error":
      return messageShown(LINE_PREFIX + String(reply.line) + ": " + reply.message);
    case "simulation_failed":
      return messageShown(SIMULATION_FAILED_PREFIX + reply.message);
    case "unexpected_status":
      return messageShown(UNEXPECTED_STATUS_PREFIX + String(reply.status));
    case "cannot_read":
      return messageShown(CANNOT_READ);
  }
}
