export function CodePane(props: {
  code: string;
  onChange: (code: string) => void;
  demoName: string | null;
  codeMessage: string | null;
}) {
  return (
    <div className="code-pane" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {props.demoName !== null ? <p className="demo-name">{props.demoName}</p> : null}
      <textarea
        aria-label="C source"
        style={{ flex: "1 1 0", minHeight: 120, width: "100%", boxSizing: "border-box" }}
        value={props.code}
        onChange={(event) => props.onChange(event.target.value)}
      />
      {props.codeMessage !== null ? <p>{props.codeMessage}</p> : null}
    </div>
  );
}
