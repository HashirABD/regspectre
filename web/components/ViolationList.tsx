import { LIVE_LABEL, NOT_FROM_C, NO_VIOLATIONS, RECORDED_LABEL_PREFIX } from "../lib/messages";
import type { Shown } from "../lib/registerCells";

export function ViolationList(props: { shown: Shown }) {
  const shown = props.shown;
  if (shown.kind !== "live" && shown.kind !== "recorded") {
    return null;
  }

  const label = shown.kind === "live" ? LIVE_LABEL : RECORDED_LABEL_PREFIX + shown.createdUtc;

  return (
    <div className="violation-list">
      <p className="source-label">{label}</p>
      {shown.violations.length === 0 ? (
        <p>{NO_VIOLATIONS}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th scope="col">register</th>
              <th scope="col">bit</th>
              <th scope="col">intended</th>
              <th scope="col">actual</th>
              <th scope="col">cycle</th>
              <th scope="col">c_line</th>
            </tr>
          </thead>
          <tbody>
            {shown.violations.map((violation, n) => (
              <tr key={n}>
                <td>{violation.register}</td>
                <td>{violation.bit}</td>
                <td>{violation.intended}</td>
                <td>{violation.actual}</td>
                <td>{violation.cycle}</td>
                <td>{violation.c_line ?? NOT_FROM_C}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
