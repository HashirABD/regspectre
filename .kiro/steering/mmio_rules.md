# Bare metal MMIO rules for firmware in this repository

1. Never use compound assignment (|=, &=, ^=) on a register that contains write one to clear or write zero to clear bits. Use direct assignment such as REG = (1U << BIT).
2. Always access peripheral registers through volatile qualified pointers.
3. Never read a register that contains read to clear bits more than once per interrupt handler. Read it once into a local variable and reuse that value.
4. Write the unlock key to a lock register before writing a locked control register, and enable the peripheral clock before any other register access.
