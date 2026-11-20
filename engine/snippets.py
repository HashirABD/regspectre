"""Demo C snippets for the UART_ISR and UART_RDR replays.

Pure Python. This module imports nothing.
"""

DEMO_SNIPPET_NAMES = (
    "ISR_RMW_SNIPPET",
    "ISR_DIRECT_SNIPPET",
    "RDR_DOUBLE_READ_SNIPPET",
    "RDR_SINGLE_READ_SNIPPET",
)

# Interrupt handler that sets TX_DONE with a read-modify-write. This is the bug.
ISR_RMW_SNIPPET = """void uart_isr(void) {
    UART_ISR |= (1U << TX_DONE);
}
"""

# The same handler written as a direct assignment. This form is safe.
ISR_DIRECT_SNIPPET = """void uart_isr(void) {
    UART_ISR = (1U << TX_DONE);
}
"""

# Interrupt handler that reads UART_RDR twice. The second read sees the register that
# the first read cleared, so the received data is lost. This is the read-to-clear bug.
RDR_DOUBLE_READ_SNIPPET = """void uart_rdr_twice(void) {
    uint8_t first = UART_RDR;
    uint8_t second = UART_RDR;
}
"""

# Interrupt handler that reads UART_RDR once. This is the safe form.
RDR_SINGLE_READ_SNIPPET = """void uart_rdr_once(void) {
    uint8_t first = UART_RDR;
}
"""

DEMO_SOURCES = (
    ("ISR_RMW_SNIPPET", ISR_RMW_SNIPPET),
    ("ISR_DIRECT_SNIPPET", ISR_DIRECT_SNIPPET),
    ("RDR_DOUBLE_READ_SNIPPET", RDR_DOUBLE_READ_SNIPPET),
    ("RDR_SINGLE_READ_SNIPPET", RDR_SINGLE_READ_SNIPPET),
)
