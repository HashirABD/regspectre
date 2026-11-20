export function Message(props: { text: string | null }) {
  if (props.text === null) {
    return null;
  }
  return <p role="status">{props.text}</p>;
}
