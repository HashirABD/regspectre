export function SnippetSelector(props: {
  names: readonly string[];
  selected: string;
  onSelect: (name: string) => void;
}) {
  return (
    <select
      aria-label="Demo snippet"
      value={props.selected}
      onChange={(event) => props.onSelect(event.target.value)}
    >
      {props.names.map((name) => (
        <option key={name} value={name}>
          {name}
        </option>
      ))}
    </select>
  );
}
