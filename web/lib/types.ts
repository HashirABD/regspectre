export type Register = "UART_ISR" | "UART_RDR";
export type Violation = { register: Register; bit: number; intended: number; actual: number; cycle: number; c_line?: number };
export type Replayed = { register: Register; pre: number; post: number };
export type DemoSnippet = { name: string; source: string };
export type SnapshotRecord = { name: string; source: string; violations: Violation[]; replayed: Replayed | null };
export type Snapshot = { createdUtc: string; records: SnapshotRecord[] };
export type Result<T> = { ok: true; value: T } | { ok: false };
