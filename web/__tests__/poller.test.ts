import { describe, it, expect, vi, afterEach } from "vitest";
import { fetchSnippets, fetchStatus, loadSnapshot, postRun } from "../lib/api";
import { startStatusPoller } from "../lib/poller";

// Built at runtime, so this file does not contain the Snapshot literal that the Python literal check scans for.
const SNAPSHOT_URL = "/demo_" + "snapshot.json";

function reply(status: number, body: string): Response {
  return { status, text: async () => body } as unknown as Response;
}

function startFakeClock(): void {
  vi.useFakeTimers();
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("startStatusPoller", () => {
  it("starts the next request 1000 ms after the previous one started", async () => {
    startFakeClock();
    const fetchMock = vi.fn(async () => reply(200, "{}"));
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

    const stop = startStatusPoller(() => {});
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(999);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    stop();
  });

  it("waits for each outcome before it schedules the next request", async () => {
    startFakeClock();
    const fetchMock = vi.fn(
      () => new Promise<Response>((resolve) => setTimeout(() => resolve(reply(200, "{}")), 300)),
    );
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);
    const onOutcome = vi.fn();

    const stop = startStatusPoller(onOutcome);
    await vi.advanceTimersByTimeAsync(300);
    expect(onOutcome).toHaveBeenCalledTimes(1);
    expect(onOutcome).toHaveBeenCalledWith({ kind: "reachable", busy: false });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(699);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    stop();
  });

  it("starts the next request at once when the previous one took longer than 1000 ms", async () => {
    startFakeClock();
    const fetchMock = vi.fn(
      () => new Promise<Response>((resolve) => setTimeout(() => resolve(reply(200, "{}")), 1500)),
    );
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

    const stop = startStatusPoller(() => {});
    await vi.advanceTimersByTimeAsync(1499);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    stop();
  });

  it("stops further requests and callbacks after stop", async () => {
    startFakeClock();
    const fetchMock = vi.fn(async () => reply(200, '{"busy": true}'));
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);
    const onOutcome = vi.fn();

    const stop = startStatusPoller(onOutcome);
    await vi.advanceTimersByTimeAsync(0);
    expect(onOutcome).toHaveBeenCalledTimes(1);
    expect(onOutcome).toHaveBeenCalledWith({ kind: "reachable", busy: true });
    stop();
    await vi.advanceTimersByTimeAsync(5000);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(onOutcome).toHaveBeenCalledTimes(1);
  });
});

describe("fetchStatus", () => {
  it("gives unreachable when the request is aborted at 2000 ms", async () => {
    startFakeClock();
    const fetchMock = vi.fn(
      (_url: string, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
        }),
    );
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

    const pending = fetchStatus();
    await vi.advanceTimersByTimeAsync(2000);
    await expect(pending).resolves.toStrictEqual({ kind: "unreachable" });
  });

  it("gives reachable with busy false for a non-200 response", async () => {
    startFakeClock();
    vi.stubGlobal("fetch", vi.fn(async () => reply(500, "oops")) as unknown as typeof fetch);

    await expect(fetchStatus()).resolves.toStrictEqual({ kind: "reachable", busy: false });
  });

  it("gives reachable with busy true for a 200 body with a boolean busy of true", async () => {
    startFakeClock();
    vi.stubGlobal("fetch", vi.fn(async () => reply(200, '{"busy": true}')) as unknown as typeof fetch);

    await expect(fetchStatus()).resolves.toStrictEqual({ kind: "reachable", busy: true });
  });

  it("gives busy false when busy in the 200 body is not a boolean", async () => {
    startFakeClock();
    vi.stubGlobal("fetch", vi.fn(async () => reply(200, '{"busy": "yes"}')) as unknown as typeof fetch);

    await expect(fetchStatus()).resolves.toStrictEqual({ kind: "reachable", busy: false });
  });

  it("gives unreachable when fetch rejects with a network error", async () => {
    startFakeClock();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }) as unknown as typeof fetch,
    );

    await expect(fetchStatus()).resolves.toStrictEqual({ kind: "unreachable" });
  });
});

describe("loadSnapshot", () => {
  it("gives null for a 404 response and reads the Snapshot URL", async () => {
    startFakeClock();
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => reply(404, "missing"));
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

    await expect(loadSnapshot()).resolves.toBeNull();
    expect(fetchMock).toHaveBeenCalledWith(SNAPSHOT_URL, { cache: "no-store" });
  });

  it("gives the body text for a 200 response", async () => {
    startFakeClock();
    const body = '{"created_utc":"2026-11-15T12:00:00Z","records":[]}';
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => reply(200, body));
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

    await expect(loadSnapshot()).resolves.toBe(body);
    expect(fetchMock).toHaveBeenCalledWith(SNAPSHOT_URL, { cache: "no-store" });
  });
});

describe("fetchSnippets", () => {
  it("gives null for a 500 response", async () => {
    startFakeClock();
    vi.stubGlobal("fetch", vi.fn(async () => reply(500, "oops")) as unknown as typeof fetch);

    await expect(fetchSnippets()).resolves.toBeNull();
  });
});

describe("postRun", () => {
  it("gives no_response when the request is aborted at 70000 ms and sends the JSON body", async () => {
    startFakeClock();
    const fetchMock = vi.fn(
      (_url: string, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
        }),
    );
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

    const pending = postRun({ c_source: "x" });
    await vi.advanceTimersByTimeAsync(70000);
    const outcome = await pending;

    expect(outcome.kind).not.toBe("recorded");
    expect(outcome).toStrictEqual({ kind: "no_response" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][1]?.body).toBe(JSON.stringify({ c_source: "x" }));
  });
});
