export function RunControl(props: { enabled: boolean; onRun: () => void }) {
  return (
    <button type="button" disabled={!props.enabled} onClick={() => props.onRun()}>
      Run
    </button>
  );
}
