import {
  DISCLAIMER_1,
  DISCLAIMER_2,
  DISCLAIMER_3,
  DISCLAIMER_4,
  DISCLAIMER_5,
  REPLAYED_NOTE_1,
  REPLAYED_NOTE_2,
} from "../lib/messages";

const DISCLAIMERS = [DISCLAIMER_1, DISCLAIMER_2, DISCLAIMER_3, DISCLAIMER_4, DISCLAIMER_5];
const REPLAYED_NOTES = [REPLAYED_NOTE_1, REPLAYED_NOTE_2];

export function Disclaimers(props: { showReplayedNotes: boolean }) {
  return (
    <div className="disclaimers">
      <ul>
        {DISCLAIMERS.map((text) => (
          <li key={text}>{text}</li>
        ))}
      </ul>
      {props.showReplayedNotes ? (
        <ul>
          {REPLAYED_NOTES.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
