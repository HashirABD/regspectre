"use client";

import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { CodePane } from "../components/CodePane";
import { Disclaimers } from "../components/Disclaimers";
import { Message } from "../components/Message";
import { RegisterArray } from "../components/RegisterArray";
import { RunControl } from "../components/RunControl";
import { SnippetSelector } from "../components/SnippetSelector";
import { ViolationList } from "../components/ViolationList";
import { WaveformPlaceholder } from "../components/WaveformPlaceholder";
import { postRun } from "../lib/api";
import { RECORDED_UNAVAILABLE, SOURCES_UNAVAILABLE, UNREACHABLE_USER } from "../lib/messages";
import { startStatusPoller } from "../lib/poller";
import { buildRegisterCells } from "../lib/registerCells";
import type { Shown } from "../lib/registerCells";
import { outcomeShown, routeRun, startRun, userTooLargeShown } from "../lib/runState";
import type { BackendState } from "../lib/runState";
import { demoNameFor, runBody } from "../lib/snippetState";
import { DEMO_ORDER, loadDemoSources, sourceFor } from "../lib/sources";
import type { Register, Snapshot } from "../lib/types";

const FIRST_SNIPPET = "ISR_RMW_SNIPPET";
const WAVEFORM_HEIGHT = 200;

const mainStyle: CSSProperties = {
  display: "grid",
  gridTemplateAreas: '"header header" "code results" "waveform waveform"',
  gridTemplateRows: `auto minmax(0, 1fr) ${WAVEFORM_HEIGHT}px`,
  gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)",
  gap: 16,
  padding: 16,
  height: "100vh",
  boxSizing: "border-box",
  overflow: "hidden",
};

const headerStyle: CSSProperties = { gridArea: "header" };
const codeStyle: CSSProperties = { gridArea: "code", minWidth: 0, minHeight: 0, overflow: "auto" };
const resultsStyle: CSSProperties = { gridArea: "results", minWidth: 0, minHeight: 0, overflow: "auto" };
const waveformStyle: CSSProperties = { gridArea: "waveform", height: WAVEFORM_HEIGHT };

export default function StudioPage() {
  const [sources, setSources] = useState<Record<string, string>>({});
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [sourcesReady, setSourcesReady] = useState(false);
  const [selected, setSelected] = useState<string>(FIRST_SNIPPET);
  const [code, setCode] = useState<string>("");
  const [backend, setBackend] = useState<BackendState>({ kind: "unknown" });
  const [shown, setShown] = useState<Shown>({ kind: "empty" });
  const [pending, setPending] = useState(false);
  const [register, setRegister] = useState<Register>("UART_ISR");

  useEffect(() => {
    let cancelled = false;
    void loadDemoSources().then((loaded) => {
      if (cancelled) {
        return;
      }
      setSources(loaded.sources);
      setSnapshot(loaded.snapshot);
      const isrSource = sourceFor(loaded.sources, FIRST_SNIPPET);
      if (isrSource !== null) {
        setSelected(FIRST_SNIPPET);
        setCode(isrSource);
      }
      setSourcesReady(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const stop = startStatusPoller((outcome) =>
      setBackend(
        outcome.kind === "unreachable"
          ? { kind: "unreachable" }
          : { kind: "reachable", busy: outcome.busy },
      ),
    );
    return stop;
  }, []);

  const demoName = demoNameFor(code, selected, sources);
  const selectedSource = sourceFor(sources, selected);
  const codeMessage = sourcesReady && selectedSource === null ? SOURCES_UNAVAILABLE : null;
  const canRun =
    !pending && (backend.kind === "unreachable" || (backend.kind === "reachable" && !backend.busy));
  const cells = buildRegisterCells(register, shown);
  const showReplayedNotes =
    (shown.kind === "live" || shown.kind === "recorded") && shown.replayed !== null;

  function onSelect(name: string): void {
    setSelected(name);
    const source = sourceFor(sources, name);
    if (source !== null) {
      setCode(source);
    }
  }

  async function onRun(): Promise<void> {
    const source = demoName !== null ? "demo" : "user";
    const route = routeRun(backend, source);
    if (route === "disabled") {
      return;
    }

    if (source === "user") {
      const tooLarge = userTooLargeShown(code);
      if (tooLarge !== null) {
        setShown(tooLarge);
        return;
      }
    }

    if (route === "recorded") {
      const record = snapshot?.records.find((candidate) => candidate.name === demoName);
      if (snapshot === null || record === undefined) {
        setShown({ kind: "message", text: RECORDED_UNAVAILABLE });
      } else {
        setShown({
          kind: "recorded",
          createdUtc: snapshot.createdUtc,
          violations: record.violations,
          replayed: record.replayed,
        });
      }
      return;
    }

    if (route === "unreachable_user") {
      setShown({ kind: "message", text: UNREACHABLE_USER });
      return;
    }

    // The only route left is "send".
    const started = startRun();
    setPending(true);
    setShown(started.shown);
    try {
      const outcome = await postRun(runBody(code, demoName));
      setShown(outcomeShown(outcome));
    } finally {
      setPending(false);
    }
  }

  return (
    <main style={mainStyle}>
      <div style={headerStyle}>
        <Disclaimers showReplayedNotes={showReplayedNotes} />
      </div>

      <div style={codeStyle}>
        <CodePane
          code={code}
          onChange={(newCode) => setCode(newCode)}
          demoName={demoName}
          codeMessage={codeMessage}
        />
        <SnippetSelector names={DEMO_ORDER} selected={selected} onSelect={onSelect} />
        <RunControl
          enabled={canRun}
          onRun={() => {
            void onRun();
          }}
        />
      </div>

      <div style={resultsStyle}>
        <RegisterArray
          register={register}
          onRegisterChange={(next) => setRegister(next)}
          cells={cells}
        />
        <ViolationList shown={shown} />
        <Message text={shown.kind === "message" ? shown.text : null} />
      </div>

      <div style={waveformStyle}>
        <WaveformPlaceholder />
      </div>
    </main>
  );
}
