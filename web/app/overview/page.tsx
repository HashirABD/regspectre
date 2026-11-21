import Link from "next/link";
import { StatusBar } from "../../components/StatusBar";

const CARD_STYLE = {
  background: "var(--surface-raised)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  padding: 20,
  display: "grid",
  gap: 8,
} as const;

export default function OverviewPage() {
  return (
    <div>
      <StatusBar connection="idle" current="overview" />
      <main style={{ maxWidth: 960, margin: "0 auto", padding: "48px 24px", display: "grid", gap: 32 }}>
        <section style={{ display: "grid", gap: 16 }}>
          <h1 style={{ fontSize: 36, lineHeight: 1.15, fontWeight: 700, letterSpacing: "-0.02em" }}>
            <span style={{ display: "block", color: "var(--text)" }}>Catch silent hardware register bugs</span>
            <span style={{ display: "block", color: "var(--accent)" }}>before firmware hits real silicon.</span>
          </h1>
          <p style={{ color: "var(--text-muted)", maxWidth: 680 }}>
            RegSpectre replays C firmware register accesses against real SystemVerilog RTL through cocotb and
            Icarus Verilog. Detection is deterministic, and no LLM guesses at results.
          </p>
          <div>
            <Link href="/" className="btn-primary" style={{ display: "inline-block" }}>
              Open Studio
            </Link>
          </div>
        </section>

        <section style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
          <article style={CARD_STYLE}>
            <h2 style={{ fontSize: 16, fontWeight: 600 }}>W1C Read-Modify-Write (RMW) neighbor wipeout</h2>
            <p style={{ color: "var(--text-muted)" }}>
              On UART_ISR, a read-modify-write writes back the other pending bits as 1. In a write-one-to-clear
              register, those bits are cleared.
            </p>
            <p className="mono" style={{ fontSize: 12, color: "var(--text-muted)" }}>
              ISR_RMW_SNIPPET, control: ISR_DIRECT_SNIPPET
            </p>
          </article>
          <article style={CARD_STYLE}>
            <h2 style={{ fontSize: 16, fontWeight: 600 }}>Read-to-Clear (RTC) destructive double-read</h2>
            <p style={{ color: "var(--text-muted)" }}>
              Reading UART_RDR returns the received byte and clears it. A second read returns 0, so the data is lost.
            </p>
            <p className="mono" style={{ fontSize: 12, color: "var(--text-muted)" }}>
              RDR_DOUBLE_READ_SNIPPET, control: RDR_SINGLE_READ_SNIPPET
            </p>
          </article>
        </section>
      </main>
    </div>
  );
}
