// The three example cards shown before the first run. Each card loads its demo snippet through the existing onSelect handler.
const EXAMPLES = [
  {
    name: "ISR_RMW_SNIPPET",
    title: "W1C neighbor wipeout",
    description: "A read-modify-write of UART_ISR wipes a pending neighbor bit.",
  },
  {
    name: "RDR_DOUBLE_READ_SNIPPET",
    title: "RTC double-read loss",
    description: "The second read of UART_RDR returns 0, so the received byte is lost.",
  },
  {
    name: "ISR_DIRECT_SNIPPET",
    title: "Safe direct write control",
    description: "A direct write to UART_ISR leaves the pending neighbor bit set.",
  },
];

export function ExampleCards(props: { onSelect: (name: string) => void }) {
  return (
    <section aria-label="Example snippets">
      <div className="example-card-grid">
        {EXAMPLES.map((example) => (
          <button
            key={example.name}
            type="button"
            className="example-card"
            onClick={() => props.onSelect(example.name)}
          >
            <span className="mono">{example.name}</span>
            <span>{example.title}</span>
            <span className="example-card-description">{example.description}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
