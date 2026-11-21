"use client";

import { useEffect, useState } from "react";
import type { CSSProperties } from "react";

export function CodePane(props: {
  code: string;
  onChange: (code: string) => void;
  demoName: string | null;
  codeMessage: string | null;
}) {
  const [expanded, setExpanded] = useState(false);

  // Escape closes the expanded view. The listener exists only while the view is open.
  useEffect(() => {
    if (!expanded) {
      return;
    }
    function onKey(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        setExpanded(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [expanded]);

  const cardStyle: CSSProperties = expanded
    ? {
        position: "fixed",
        inset: "64px 24px 24px 24px",
        zIndex: 50,
        display: "flex",
        flexDirection: "column",
        boxShadow: "0 20px 60px rgba(0, 0, 0, 0.7)",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        overflow: "hidden",
      }
    : {
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        overflow: "hidden",
      };

  const areaStyle: CSSProperties = expanded
    ? { flex: "1 1 auto", height: "100%", maxHeight: "none", resize: "none" }
    : { height: "160px", minHeight: "100px", maxHeight: "260px", resize: "vertical" };

  return (
    <div>
      <div className="code-card" style={cardStyle}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 8,
            background: "var(--surface-raised)",
            borderBottom: "1px solid var(--border)",
            padding: "6px 12px",
          }}
        >
          {props.demoName !== null ? (
            <p
              className="demo-name mono"
              style={{ margin: 0, fontSize: "12px", color: "var(--text-muted)" }}
            >
              {props.demoName}
            </p>
          ) : (
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Custom C snippet</span>
          )}
          <button
            type="button"
            aria-expanded={expanded}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? "Collapse" : "Expand"}
          </button>
        </div>
        <textarea
          aria-label="C source"
          style={{
            display: "block",
            width: "100%",
            maxWidth: "100%",
            boxSizing: "border-box",
            border: "none",
            borderRadius: 0,
            background: "var(--surface)",
            padding: "10px 12px",
            overflow: "auto",
            ...areaStyle,
          }}
          value={props.code}
          onChange={(event) => props.onChange(event.target.value)}
        />
      </div>
      {props.codeMessage !== null ? <p style={{ margin: "4px 0" }}>{props.codeMessage}</p> : null}
    </div>
  );
}
