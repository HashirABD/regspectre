# Requirements Document

## Introduction

The uart_core feature adds the first RegSpectre co-verification core for a UART peripheral. It supplies the SystemVerilog RTL for the UART interrupt status register (UART_ISR) and the receive data register (UART_RDR), plus a deterministic Python engine that drives that RTL through cocotb on Icarus Verilog. The engine replays the register accesses a C firmware driver would perform and reports every register bit that changed without the firmware intending it. The engine detects the write-one-to-clear neighbor corruption caused by a read-modify-write access and the data loss caused by reading a read-to-clear register twice in one interrupt handler.

## Glossary

- **UART_Core**: the SystemVerilog RTL module `rtl/uart_ctrl.sv`.
- **Bus_Interface**: the register access port of the UART_Core consisting of `clk`, `rst_n`, `we`, `re`, `addr`, `wdata`, and `rdata`.
- **UART_ISR**: the interrupt status register at address 0x40001004.
- **UART_RDR**: the receive data register at address 0x40001008.
- **TX_DONE**: UART_ISR bit 0, write one to clear.
- **RX_READY**: UART_ISR bit 1, read only.
- **PARITY_ERR**: UART_ISR bit 2, write one to clear.
- **OVERRUN_ERR**: UART_ISR bit 3, write one to clear.
- **hw_set**: the hardware set input that sets the interrupt bits of UART_ISR.
- **rx_valid**: the hardware input that signals new receive data is available.
- **rx_data**: the 8-bit hardware input bus that supplies receive data to UART_RDR.
- **W1C**: write one to clear; writing a one clears the bit and writing a zero leaves it unchanged.
- **Read_to_Clear**: a register bit that clears when the register is read.
- **Engine**: the deterministic Python verification program in `engine/`.
- **Intended_State**: the register bit value the firmware operation was expected to produce.
- **Actual_State**: the register bit value observed in the RTL after the firmware operation.
- **Read_Modify_Write**: a register access that reads the register, alters a copy, and writes it back.
- **Direct_Assignment**: a register write of the form `REG = (1U << BIT)` that does not read the register first.
- **Violation_Report**: the JSON record emitted by the Engine for an unintended bit change.
- **Interrupt_Handler**: the firmware function that services a UART interrupt.

## Requirements

### Requirement 1: UART_Core register map and bus interface

**User Story:** As a verification engineer, I want the UART_Core to implement UART_ISR and UART_RDR behind a simple bus, so that the Engine can drive real RTL with plain register transactions.

#### Acceptance Criteria

1. THE UART_Core SHALL expose UART_ISR (bits 0 to 3) at address 0x40001004 and UART_RDR (bits 7 to 0) at address 0x40001008 through the Bus_Interface.
2. WHEN a one is written to a W1C bit (bit 0 TX_DONE, bit 2 PARITY_ERR, or bit 3 OVERRUN_ERR) of UART_ISR, THE UART_Core SHALL clear that bit.
3. WHEN the hw_set input for an interrupt bit is asserted, THE UART_Core SHALL set that interrupt bit.
4. IF firmware writes a zero to a W1C bit of UART_ISR, THEN THE UART_Core SHALL leave that bit unchanged.
5. WHEN rst_n is low, THE UART_Core SHALL set UART_ISR and UART_RDR to 0.
6. WHEN rx_valid is asserted, THE UART_Core SHALL load UART_RDR with rx_data[7:0] and set RX_READY.
7. IF hw_set for an interrupt bit and a write of one to that same W1C bit occur in the same clock cycle, THEN THE UART_Core SHALL leave that bit set.
8. IF firmware writes to RX_READY, bit 1 of UART_ISR, THEN THE UART_Core SHALL leave RX_READY unchanged.

### Requirement 2: UART_RDR read-to-clear behavior

**User Story:** As a verification engineer, I want UART_RDR to clear on read, so that the Engine can detect double-read data loss.

#### Acceptance Criteria

1. WHEN UART_RDR is read, THE UART_Core SHALL return the current value of bits 7:0, then clear UART_RDR and clear RX_READY.

### Requirement 3: Engine replays firmware register operations

**User Story:** As a verification engineer, I want the Engine to replay firmware register accesses, so that the RTL sees the same transactions a C driver would issue.

#### Acceptance Criteria

1. THE Engine SHALL drive the UART_Core through cocotb on Icarus Verilog by issuing Bus_Interface transactions, where each transaction drives the we, re, addr, and wdata signals and captures rdata.
2. THE Engine SHALL replay reads, writes, and Read_Modify_Writes that a C firmware driver performs, issuing them in the same sequence the driver would issue them.
3. WHEN the Engine performs a Read_Modify_Write, THE Engine SHALL read the target register, compute a new value by setting or clearing the specified bits in the read value, and write the computed value back to the same register address.
4. THE Engine SHALL parse a C firmware snippet using a small subset of C consisting of register assignment, compound assignment with |= or &=, register reads, and simple handler functions, and convert each parsed operation to Bus_Interface transactions.
5. THE Engine SHALL NOT perform full C compilation of the firmware snippet.

### Requirement 4: Intended state versus actual state

**User Story:** As a verification engineer, I want the Engine to compare intended and actual register state, so that unintended bit changes are visible.

#### Acceptance Criteria

1. WHEN a firmware operation completes, THE Engine SHALL compute the Intended_State by modeling the register bit modifications the firmware operation was expected to produce.
2. WHEN the bus transaction completes, THE Engine SHALL read the Actual_State from the UART_Core.
3. IF the Actual_State contains one or more bits that differ from the Intended_State, THEN the Engine SHALL flag those bits as unintended changes.
4. WHEN a firmware operation names a bit mask M, THE Engine SHALL set the Intended_State of every bit outside M to its value before the operation.

### Requirement 5: W1C neighbor corruption detection

**User Story:** As a firmware author, I want the Engine to catch a read-modify-write that clears a neighbor interrupt bit, so that I do not lose a pending interrupt I meant to keep.

#### Acceptance Criteria

1. WHEN a Read_Modify_Write on UART_ISR clears a W1C bit that was pending and not intended to be cleared, THE Engine SHALL emit a Violation_Report containing that bit index, Intended_State 1, Actual_State 0, and the clock cycle.
2. WHEN a Direct_Assignment write clears only its target bit, THE Engine SHALL NOT emit a Violation_Report.
3. WHEN the Read_Modify_Write operation originates from a C snippet, THE Engine SHALL include the C source line in the Violation_Report.

### Requirement 6: Read-to-clear double read detection

**User Story:** As a firmware author, I want the Engine to catch a second read of UART_RDR in one handler, so that I do not silently lose received data.

#### Acceptance Criteria

1. IF UART_RDR is read a second time within one Interrupt_Handler, THEN THE Engine SHALL emit one Violation_Report for each bit that was 1 before the first read and is 0 on the second read, with the register name UART_RDR, that bit index, Intended_State 1, Actual_State 0, and the clock cycle.
2. IF UART_RDR is read once within one Interrupt_Handler, THEN THE Engine SHALL NOT emit a Violation_Report.

### Requirement 7: Violation report content

**User Story:** As a verification engineer, I want each violation emitted as structured JSON, so that reports can be stored and displayed.

#### Acceptance Criteria

1. THE Engine SHALL emit each Violation_Report as valid JSON containing all of the bit index as a non-negative integer, the Intended_State as 0 or 1, the Actual_State as 0 or 1, and the clock cycle as a non-negative integer.
2. WHEN the firmware operation originates from a C snippet, THE Engine SHALL include the C source line in the Violation_Report.
3. WHEN the firmware operation originates from a raw transaction list, THE Engine SHALL omit the C source line from the Violation_Report.

### Requirement 8: Deterministic engine with no LLM calls

**User Story:** As a verification engineer, I want the Engine to be deterministic and LLM-free, so that a violation is decided by code, not by a model.

#### Acceptance Criteria

1. WHEN the Engine processes the same input, defined as identical RTL file, identical C snippet, and identical hw_set timing seed, on two or more consecutive runs, THE Engine SHALL produce identical violation decisions on every run.
2. THE Engine SHALL decide whether a violation exists and classify register bits using only deterministic Python rules, without invoking any LLM for either task.

### Requirement 9: Property tests for random hardware timing

**User Story:** As a verification engineer, I want Hypothesis to inject random interrupt timing, so that Direct_Assignment writes are tested against neighbor bit wipeout.

#### Acceptance Criteria

1. WHEN the property-based test executes with Hypothesis-generated random hw_set timing applied to the UART_ISR interrupt bits across clock cycles, THE Engine SHALL verify that a Direct_Assignment write of the form UART_ISR = (1U << BIT) does not clear (transition from set to cleared) any W1C bit of UART_ISR other than bit BIT.
2. WHERE Hypothesis drives the property-based test, THE Engine SHALL generate at least 100 examples of random hw_set timing scenarios, each scenario independently asserting or deasserting each UART_ISR interrupt bit on randomly chosen clock cycles.
3. IF a Direct_Assignment write clears a W1C bit of UART_ISR other than the targeted bit BIT, THEN THE Engine SHALL fail the test with an indication that a neighbor W1C bit was wiped out by the write.
4. THE Engine SHALL describe property-based test output and documentation as randomized testing, not as proof of correctness of the UART_Core.