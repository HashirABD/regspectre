import Link from "next/link";

// The connection state shown in the pill. "live" is shown only while the backend answers the status request.
// "recorded" is shown only while Recorded_Output is displayed, and "offline" when the backend does not answer.
export type ConnectionState = "checking" | "live" | "recorded" | "offline" | "idle";

const PILLS: Record<ConnectionState, { label: string; className: string }> = {
  checking: { label: "Checking backend", className: "pill pill-muted" },
  live: { label: "Live", className: "pill pill-pass" },
  recorded: { label: "Recorded", className: "pill pill-warning" },
  offline: { label: "Offline", className: "pill pill-warning" },
  idle: { label: "Not checked", className: "pill pill-muted" },
};

export function StatusBar(props: { connection: ConnectionState; current: "studio" | "overview" }) {
  const pill = PILLS[props.connection];
  return (
    <header className="status-bar">
      <span className="accent-dot" aria-hidden="true" />
      <span className="wordmark">RegSpectre</span>
      <span className="subtitle">{"C Firmware \u2194 SystemVerilog RTL"}</span>
      <span className="badge-file" title="rtl/uart_ctrl.sv">
        uart_ctrl.sv
      </span>
      <span style={{ flex: 1 }} />
      <span className={pill.className} role="status">
        {pill.label}
      </span>
      <nav aria-label="Pages" style={{ display: "flex", gap: 4 }}>
        <Link href="/" className="nav-link" aria-current={props.current === "studio" ? "page" : undefined}>
          Studio
        </Link>
        <Link href="/overview" className="nav-link" aria-current={props.current === "overview" ? "page" : undefined}>
          Overview
        </Link>
      </nav>
    </header>
  );
}
