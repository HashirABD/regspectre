export function RunControl(props: { enabled: boolean; onRun: () => void }) {
  return (
    <button type="button" className="btn-primary" disabled={!props.enabled} onClick={() => props.onRun()}>
      Run
    </button>
  );
}
