import { fetchStatus, type StatusOutcome } from "./api";
import { STATUS_INTERVAL_MS } from "./config";

// Starts the status polling loop (design 6.4) and returns a stop function.
// Each request starts STATUS_INTERVAL_MS after the previous one started, or at once when the previous one took longer.
// The next request is scheduled only after the current outcome has been delivered.
export function startStatusPoller(
  onOutcome: (outcome: StatusOutcome) => void,
  fetchOnce: () => Promise<StatusOutcome> = fetchStatus,
): () => void {
  let stopped = false;
  let timer: ReturnType<typeof setTimeout> | undefined;

  async function poll(): Promise<void> {
    const start = Date.now();
    const outcome = await fetchOnce();
    if (stopped) {
      return;
    }
    onOutcome(outcome);
    if (stopped) {
      return;
    }
    const delay = Math.max(0, STATUS_INTERVAL_MS - (Date.now() - start));
    if (delay === 0) {
      void poll();
      return;
    }
    timer = setTimeout(() => {
      timer = undefined;
      void poll();
    }, delay);
  }

  void poll();

  return () => {
    stopped = true;
    if (timer !== undefined) {
      clearTimeout(timer);
      timer = undefined;
    }
  };
}
