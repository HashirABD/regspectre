import { NOT_FROM_C, WAVEFORM_PLACEHOLDER } from "../lib/messages";
import type { Shown } from "../lib/registerCells";
import type { Register, Replayed } from "../lib/types";

// Bit width of each register, used to pad hex text. From rtl/uart_ctrl.sv.
const WIDTH: Record<Register, number> = { UART_ISR: 4, UART_RDR: 8 };

type Tone = "accent" | "pass" | "bug";
type Pill = { key: string; text: string; tone: Tone };

function hex(value: number, width: number): string {
  return "0x" + value.toString(16).toUpperCase().padStart(Math.ceil(width / 4), "0");
}

// Pills in order: the pre state, one pill per violating C line access, then a clean or violation marker.
function timelinePills(register: Register, shown: Shown): Pill[] {
  if (shown.kind !== "live" && shown.kind !== "recorded") {
    return [];
  }
  const replayed: Replayed | null = shown.replayed;
  if (replayed === null || replayed.register !== register) {
    return [];
  }
  const violations = shown.violations
    .filter((violation) => violation.register === register)
    .sort((a, b) => a.cycle - b.cycle);
  const pills: Pill[] = [{ key: "pre", text: "pre " + hex(replayed.pre, WIDTH[register]), tone: "accent" }];
  violations.forEach((violation, n) => {
    pills.push({
      key: "access-" + n,
      text: "cycle " + violation.cycle + " C line " + (violation.c_line ?? NOT_FROM_C),
      tone: "accent",
    });
  });
  if (violations.length > 0) {
    const count = violations.length === 1 ? "1 violation" : violations.length + " violations";
    pills.push({ key: "end", text: count, tone: "bug" });
  } else {
    pills.push({ key: "end", text: "clean", tone: "pass" });
  }
  return pills;
}

// The dock is fixed at 200px by StudioPage. The disclaimer appears once, above the timeline.
export function WaveformPlaceholder(props: { register: Register; shown: Shown }) {
  const pills = timelinePills(props.register, props.shown);
  return (
    <div aria-label="Waveform" className="waveform-dock">
      <p className="waveform-note">{WAVEFORM_PLACEHOLDER}</p>
      {pills.length === 0 ? (
        <p className="timeline-empty">Run a snippet to see its register accesses.</p>
      ) : (
        <ol className="timeline" aria-label="Register access timeline">
          {pills.map((pill, n) => [
            n > 0 ? (
              <li key={pill.key + "-sep"} className="timeline-arrow" aria-hidden="true">
                &rarr;
              </li>
            ) : null,
            <li key={pill.key} className={"timeline-pill timeline-" + pill.tone}>
              {pill.text}
            </li>,
          ])}
        </ol>
      )}
    </div>
  );
}
