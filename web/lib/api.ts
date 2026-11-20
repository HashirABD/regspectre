import { BACKEND_URL, RUN_TIMEOUT_MS, STATUS_TIMEOUT_MS } from "./config";
import type { RunOutcome } from "./runState";

// Result of GET /api/status (design 6.3). Any HTTP response counts as reachable, whatever its status.
export type StatusOutcome = { kind: "reachable"; busy: boolean } | { kind: "unreachable" };

// Reads busy from a status response body. Only a JSON object whose busy value is true gives true.
// Any other body gives false (design 6.3, and C12 for non-200 responses).
async function readBusy(response: Response): Promise<boolean> {
  try {
    const parsed: unknown = JSON.parse(await response.text());
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      return false;
    }
    return (parsed as { busy?: unknown }).busy === true;
  } catch {
    return false;
  }
}

export async function fetchStatus(): Promise<StatusOutcome> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), STATUS_TIMEOUT_MS);
  try {
    const response = await fetch(`${BACKEND_URL}/api/status`, { signal: controller.signal });
    return { kind: "reachable", busy: await readBusy(response) };
  } catch {
    return { kind: "unreachable" };
  } finally {
    clearTimeout(timer);
  }
}

export async function postRun(body: unknown): Promise<RunOutcome> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), RUN_TIMEOUT_MS);
  try {
    const response = await fetch(`${BACKEND_URL}/api/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    try {
      const text = await response.text();
      return { kind: "response", status: response.status, text };
    } catch {
      // The status arrived but the body did not, so there is no text to show. Treat it as no response.
      return { kind: "no_response" };
    }
  } catch {
    return { kind: "no_response" };
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchSnippets(): Promise<string | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), STATUS_TIMEOUT_MS);
  try {
    const response = await fetch(`${BACKEND_URL}/api/snippets`, { signal: controller.signal });
    if (response.status !== 200) {
      return null;
    }
    return await response.text();
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

// The only read of the Snapshot in the Studio. The file is read-only here, and the Studio never writes it
// (Requirement 8, criterion 9).
export async function loadSnapshot(): Promise<string | null> {
  try {
    const response = await fetch("/demo_snapshot.json", { cache: "no-store" });
    if (response.status !== 200) {
      return null;
    }
    return await response.text();
  } catch {
    return null;
  }
}
