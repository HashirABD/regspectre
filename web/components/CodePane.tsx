export function CodePane(props: {
  code: string;
  onChange: (code: string) => void;
  demoName: string | null;
  codeMessage: string | null;
}) {
  return (
    <div className="code-pane">
      {props.demoName !== null ? <p className="demo-name">{props.demoName}</p> : null}
      <textarea
        aria-label="C source"
        value={props.code}
        onChange={(event) => props.onChange(event.target.value)}
      />
      {props.codeMessage !== null ? <p>{props.codeMessage}</p> : null}
    </div>
  );
}
