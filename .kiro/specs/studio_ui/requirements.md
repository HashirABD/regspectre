# Requirements Document

## Introduction

The studio_ui feature adds RegSpectre Studio, a Next.js web page in `web/` that shows a C snippet, a 32-cell register array, and a violation list built from the Engine's report. Live results come from a local FastAPI Backend. The Backend runs the Engine's real run path, which replays the C snippet on the uart_ctrl RTL in Icarus Verilog through cocotb, and returns the Violation_Report JSON unchanged, together with the Replayed_State as a separate field. When the Backend is unreachable, the Studio can show Recorded_Output for the four Demo_Snippets from a Snapshot that the Engine wrote from a real demo run. The Studio displays the report and the Replayed_State only. It does not compute violations.

The Studio replays a small C subset. It is not a full C compiler, and it does not simulate a whole chip. The waveform view and the one-click auto fix are later features. This feature reserves a waveform region in the layout and places no waveform data and no fix action in it.

## Glossary

- **Studio**: the RegSpectre web page in `web/`, built with Next.js, that shows the code pane, Run_Control, the snippet selector, the Register_Array, the Violation_List, and the Waveform_Placeholder.
- **Backend**: the local FastAPI service that accepts a Demo_Snippet name or User_Snippet text, runs the Engine, and returns the Violation_Report JSON.
- **Engine**: the deterministic Python program in `engine/` that parses C snippets, replays them on the UART_Core, and writes the Violation_Report JSON.
- **UART_Core**: the SystemVerilog module `rtl/uart_ctrl.sv`.
- **Simulation**: one run of the UART_Core in Icarus Verilog through cocotb, started by the Engine for one snippet.
- **Demo_Snippet**: one of the four fixed C snippets named ISR_RMW_SNIPPET, ISR_DIRECT_SNIPPET, RDR_DOUBLE_READ_SNIPPET, and RDR_SINGLE_READ_SNIPPET, defined in `engine/demo.py`.
- **User_Snippet**: C source text in the code pane whose content differs from the C source of the selected Demo_Snippet, or any C source text when no Demo_Snippet is selected.
- **Subset**: the small set of C forms the Engine accepts, defined in Requirement 3.
- **Parser_Error**: the error the Engine returns for a User_Snippet that contains a form outside the Subset or has invalid syntax. It holds the 1-based line number of the first rejected statement and a message.
- **Violation_Report**: the JSON array the Engine writes for one run. Each element is an object with the keys, in this order, register (string, UART_ISR or UART_RDR), bit (integer from 0 up to the register width minus 1), intended (0 or 1), actual (0 or 1), cycle (integer 0 or greater), and c_line (integer 1 or greater, present only when the statement came from C).
- **Violation_List**: the list in the Studio that shows one row for each element of a Violation_Report.
- **Register_Map**: the register names, widths, and bit names defined in `engine/regmap.py`. UART_ISR is 4 bits wide with bit names TX_DONE, RX_READY, PARITY_ERR, and OVERRUN_ERR. UART_RDR is 8 bits wide with bit names RDR[0] to RDR[7].
- **Register_Array**: the 32-cell display in the Studio for the selected register.
- **Replayed_State**: an object with the keys register, pre, and post. register is the one register that the snippet names, UART_ISR or UART_RDR. pre is the value of that register sampled before the snippet's first access to it, and post is the value sampled after its last access. Both are integers from 0 up to the register's maximum, 15 for UART_ISR and 255 for UART_RDR. The Engine measures pre and post on the uart_ctrl RTL and never assumes post. The value is null when the snippet names no register. It is also null when the snippet contains only reads of UART_ISR, with no write and no read-modify-write of UART_ISR. In that case the Engine SHALL NOT assume or invent pre or post values, and the Studio shows "not replayed" under Requirement 5, criterion 15. Replayed_State is separate from the Violation_Report. It is the state of the replayed snippet in the uart_ctrl simulation, not the state of a whole chip.
- **Unused_Cell**: a Register_Array cell whose bit index is at or above the width of the selected register.
- **Live_Result**: a Violation_Report and its Replayed_State that the Backend produced for a run request the Studio sent during the current page session.
- **Snapshot**: the file `web/public/demo_snapshot.json`, written by the Engine from a successful demo run. In each record, the report value is the Violation_Report text stored as a JSON string, in the same form as the report in a Backend response.
- **Recorded_Output**: the report and Replayed_State of a Demo_Snippet that the Studio reads from a Snapshot record, with the report stored in the same form as a Backend response.
- **Unreachable_Backend**: the condition in which the Studio's GET /api/status request receives no HTTP response within 2 seconds.
- **Busy_State**: the condition in which the Backend is running a Simulation, so every new run request receives HTTP 409.
- **Timeout**: the condition in which a Simulation runs longer than 60 seconds, so the Backend stops it and returns HTTP 504.
- **Run_Control**: the Studio button that sends a run request to the Backend or loads Recorded_Output.
- **Waveform_Placeholder**: the reserved, empty region in the Studio layout for a later waveform view.

## Requirements

### Requirement 1: Studio layout and reserved regions

**User Story:** As a verification engineer, I want the C code, the register bits, the violations, and a reserved waveform area on one page, so that I can read the results of a run in one place.

#### Acceptance Criteria

1. THE Studio SHALL display the code pane, the snippet selector, Run_Control, the Register_Array, the Violation_List, and the Waveform_Placeholder on one page at the same time.
2. THE Studio SHALL display the Waveform_Placeholder in its own region, separate from the code pane, the Register_Array, and the Violation_List, and SHALL keep the Waveform_Placeholder at the same position and size on the page whether a Violation_Report, a Live_Result, or Recorded_Output is shown, or no results are shown.
3. THE Studio SHALL display the text "Waveform view is not available in this version." inside the Waveform_Placeholder, and SHALL display no waveform data inside it.
4. THE Studio SHALL display no interactive control and no auto-fix action inside the Waveform_Placeholder.
5. WHEN a Live_Result is displayed, THE Studio SHALL display the source label "Live result" directly above the Violation_List.
6. WHEN Recorded_Output is displayed, THE Studio SHALL display the source label "Recorded output, created <time>" directly above the Violation_List, where <time> is the created_utc value of the Snapshot.
7. WHILE no Live_Result and no Recorded_Output is displayed, THE Studio SHALL display no source label above the Violation_List.

### Requirement 2: Demo snippets offered first

**User Story:** As a verification engineer, I want the four demo snippets offered first by name, so that I can replay the known UART cases without typing C.

#### Acceptance Criteria

1. WHEN the Studio loads, THE Studio SHALL list the four Demo_Snippet names as the first four entries of the snippet selector, in this order: ISR_RMW_SNIPPET, ISR_DIRECT_SNIPPET, RDR_DOUBLE_READ_SNIPPET, RDR_SINGLE_READ_SNIPPET, whether or not the Backend responds.
2. WHEN the Studio loads, THE Studio SHALL select ISR_RMW_SNIPPET in the snippet selector.
3. WHEN the Studio loads, THE Studio SHALL place the C source of ISR_RMW_SNIPPET in the code pane.
4. WHEN the user selects a Demo_Snippet name, THE Studio SHALL replace the code pane text with the C source of that Demo_Snippet.
5. THE Studio SHALL display the name of the selected Demo_Snippet directly above the code pane only while the code pane text is exactly equal, character for character, to the C source of that Demo_Snippet.
6. WHILE the code pane text is exactly equal to the C source of the selected Demo_Snippet, THE Studio SHALL send a run request that names the Demo_Snippet in the snippet field, and otherwise SHALL send the code pane text in the c_source field.
7. WHEN the Backend returns the C source of a Demo_Snippet in its response to GET /api/snippets, THE Studio SHALL use that text as the C source of the Demo_Snippet.
8. IF the Studio finds the Backend to be an Unreachable_Backend when it loads, THEN THE Studio SHALL obtain the C source of each Demo_Snippet from the Snapshot.
9. IF the Backend response to GET /api/snippets does not provide the C source of a Demo_Snippet, THEN THE Studio SHALL obtain that C source from the Snapshot.
10. IF neither the Backend nor the Snapshot provides the C source of the selected Demo_Snippet, THEN THE Studio SHALL display "The demo snippet sources could not be loaded." in the code pane.

### Requirement 3: User-typed C in the Subset

**User Story:** As a firmware author, I want to type my own C handler in the supported subset and run it, so that I can see which bits the replay changes.

#### Acceptance Criteria

1. THE Engine SHALL accept a User_Snippet only when every statement in it matches one of the forms in criteria 3 to 7 of this requirement and uses integer constants and operators only as criterion 8 of this requirement allows.
2. THE Engine SHALL keep the existing parse function in `engine/c_parser.py` unchanged, and SHALL provide a new entry point for User_Snippet text that calls that parse function first and never contains a C parser of its own.
3. THE Engine SHALL accept the direct assignment `UART_ISR = (1U << NAME);`, where NAME is TX_DONE, PARITY_ERR, or OVERRUN_ERR.
4. THE Engine SHALL accept the read-modify-write `UART_ISR |= (1U << NAME);`, where NAME is TX_DONE, PARITY_ERR, or OVERRUN_ERR.
5. THE Engine SHALL accept the read-modify-write `UART_ISR &= ~(1U << NAME);`, where NAME is TX_DONE, PARITY_ERR, or OVERRUN_ERR.
6. THE Engine SHALL accept a declaration of the form `TYPE VAR = REG;`, where TYPE is uint8_t or uint32_t, VAR is a C identifier, and REG is UART_ISR or UART_RDR, such as `uint8_t d = UART_RDR;`.
7. THE Engine SHALL accept a handler definition of the form `void NAME(void) { ... }`, where NAME is a C identifier and the body contains only statements accepted under criteria 3 to 6 of this requirement.
8. THE Engine SHALL accept integer constants, the operator `~`, the operator `|`, and the operator `&` only as parts of the forms in criteria 3 to 6 of this requirement.
9. IF a User_Snippet contains a loop, an if or else statement, a ternary expression, a function call other than a handler definition, or a pointer declaration or dereference, THEN THE Engine SHALL return a Parser_Error.
10. IF a User_Snippet contains a statement that matches none of the forms in criteria 3 to 7 of this requirement, or contains invalid C syntax, THEN THE Engine SHALL return a Parser_Error.
11. IF a User_Snippet writes to UART_RDR, THEN THE Engine SHALL return a Parser_Error.
12. IF a User_Snippet names a register other than UART_ISR or UART_RDR, THEN THE Engine SHALL return a Parser_Error.
13. IF a User_Snippet names a bit other than TX_DONE, PARITY_ERR, or OVERRUN_ERR, including RX_READY, THEN THE new entry point SHALL return a Parser_Error.
14. IF a User_Snippet contains no handler definition, THEN THE new entry point SHALL return a Parser_Error.
15. IF a User_Snippet uses both UART_ISR and UART_RDR, THEN THE new entry point SHALL return a Parser_Error for the first statement that names the register that appears second in the User_Snippet text.
16. IF a User_Snippet contains a statement outside a handler definition, THEN THE Engine SHALL return a Parser_Error for that statement.
17. WHEN the Engine returns a Parser_Error, THE Engine SHALL report only the first rejected statement in the User_Snippet text.
18. WHEN the Engine returns a Parser_Error, THE Engine SHALL report the 1-based line number on which the first rejected statement starts, or line 1 when the User_Snippet has no handler definition.
19. WHEN the Engine returns a Parser_Error, THE Engine SHALL report a message that names the rejected form.
20. WHEN the new entry point accepts a User_Snippet, THE new entry point SHALL return exactly the same operations, in the same order, as the existing parse function returns for that text.
21. WHEN a run request contains a User_Snippet, THE Backend SHALL run the new entry point on that User_Snippet before it starts any Simulation.
22. IF the new entry point returns a Parser_Error for a User_Snippet, THEN THE Backend SHALL return HTTP 422 with body {"error":"parser_error","line":N,"message":M}, where N is the 1-based line number and M is the message, and SHALL start no Simulation.
23. WHEN a User_Snippet produces a Parser_Error, THE Studio SHALL display "Line N: " followed by the message from the Parser_Error, where N is the line number, and SHALL show no Violation_List rows and no Register_Array values.
24. IF a User_Snippet is more than 200 lines or more than 8192 bytes of UTF-8 text, THEN THE Studio SHALL display "The snippet is larger than 200 lines or 8 KB and was not run." and SHALL NOT send a run request. In this criterion, a line ends at a line break or at the end of the text.
25. IF a run request contains a User_Snippet that is more than 200 lines or more than 8192 bytes of UTF-8 text, THEN THE Backend SHALL return HTTP 400 with body {"error":"too_large"} and start no Simulation.

### Requirement 4: Violation list built from the report

**User Story:** As a verification engineer, I want the violation list to show each violation from the report in order, so that I can read the Engine's results without any reinterpretation.

#### Acceptance Criteria

1. WHEN a Violation_Report that contains one or more elements is displayed, THE Studio SHALL show exactly one Violation_List row for each element of the report, including elements whose values duplicate another element's values.
2. WHEN a Violation_Report is displayed, THE Studio SHALL list the rows in the same order as the elements of the report array.
3. WHEN a Violation_Report is displayed, THE Studio SHALL show, in each row, the register, bit, intended, actual, cycle, and c_line values of that element as the report contains them, in the columns register, bit, intended, actual, cycle, and c_line, in that order, with no conversion or relabeling.
4. IF an element contains the c_line key, THEN THE Studio SHALL show the c_line value of that element in the c_line column of that element's row.
5. IF an element does not contain the c_line key, THEN THE Studio SHALL show the text "not from C" in the c_line column of that element's row.
6. THE Studio SHALL NOT add, remove, compute, or infer any violation, and SHALL display no value in a row other than the values of that element of the Violation_Report and the text required by criterion 5.
7. IF the Violation_Report is an empty array, THEN THE Studio SHALL display "The report contains no violations." and SHALL display no Violation_List rows.

### Requirement 5: Register array

**User Story:** As a verification engineer, I want a 32-cell register array for the selected register that shows the replayed register state and marks the bits the report flags, so that I can see what the replay did and which bits are violations.

#### Acceptance Criteria

1. THE Studio SHALL display a Register_Array of exactly 32 cells for the selected register.
2. THE Studio SHALL label the 32 cells with bit indexes 0 to 31 from left to right.
3. THE Studio SHALL offer a register selector whose choices are UART_ISR and UART_RDR.
4. WHEN the Studio loads, THE Studio SHALL select UART_ISR in the register selector.
5. WHEN the user selects a register in the register selector, THE Studio SHALL fill the Register_Array for that register from the currently displayed Violation_Report and Replayed_State and SHALL send no run request.
6. WHILE UART_ISR is the selected register, THE Studio SHALL label cells 0 to 3 as TX_DONE, RX_READY, PARITY_ERR, and OVERRUN_ERR, in that order.
7. WHILE UART_RDR is the selected register, THE Studio SHALL label cells 0 to 7 as RDR[0] to RDR[7], in that order.
8. WHILE UART_ISR is the selected register, THE Studio SHALL display cells 4 to 31 as Unused_Cells.
9. WHILE UART_RDR is the selected register, THE Studio SHALL display cells 8 to 31 as Unused_Cells.
10. THE Studio SHALL display each Unused_Cell with the text "unused" and SHALL NOT display a 0, a 1, a violation value, a Replayed_State value, or the text "no violation reported" in that cell, whatever the displayed Violation_Report or Replayed_State contains.
11. WHEN no Violation_Report and no Replayed_State is displayed, THE Studio SHALL display each cell inside the width of the selected register with its bit label and no 0, no 1, and no "no violation reported" or "not replayed" text.
12. WHEN a displayed Violation_Report contains one or more elements whose register equals the selected register and whose bit equals a cell's bit index, THE Studio SHALL mark that cell as a violation and SHALL display in that cell the intended value and the actual value of each such element, one intended and actual pair per line, in array order.
13. WHEN a displayed Replayed_State has a register equal to the selected register, THE Studio SHALL display in each cell inside the width the pre value and the post value of that cell's bit, as the Replayed_State gives them, and SHALL NOT derive any Replayed_State bit value from the Violation_Report.
14. WHEN a displayed Violation_Report contains no element whose register equals the selected register and whose bit equals a cell's bit index, THE Studio SHALL display the text "no violation reported" in that cell and SHALL NOT display an intended or actual value for that bit.
15. WHEN the Replayed_State is null or has a register that differs from the selected register, THE Studio SHALL display the text "not replayed" in each cell inside the width of the selected register and SHALL NOT display a 0 or a 1 as a replayed value for that bit.
16. WHEN the Studio fills the Register_Array, THE Studio SHALL use only the elements of the Violation_Report whose register equals the selected register, and SHALL keep showing all elements in the Violation_List.

### Requirement 6: Live Backend

**User Story:** As a verification engineer, I want a local backend that runs the Engine on the RTL and returns the report unchanged with the Replayed_State as a separate field, so that the Studio shows Live_Results.

#### Acceptance Criteria

1. WHEN the Backend accepts a run request, THE Backend SHALL run it on the uart_ctrl RTL in Icarus Verilog through cocotb, using the Engine's demo run path for a request with the "snippet" field and the Engine entry point for User_Snippet text defined in Requirement 3, criterion 2, for a request with the "c_source" field. That entry point is a required Engine change, because the current demo run path replays only the four Demo_Snippets.
2. THE Backend SHALL NOT cause the Snapshot to be written or changed by any run request.
3. THE Backend SHALL listen on the address 127.0.0.1 only.
4. THE Backend SHALL accept run requests with a JSON body that contains exactly one of two fields: "snippet", holding one of the four Demo_Snippet names, or "c_source", holding User_Snippet text.
5. IF a run request names a snippet that is not one of the four Demo_Snippet names, contains both fields, or contains neither field, THEN THE Backend SHALL return HTTP 400 with body {"error":"invalid_request"} and start no Simulation.
6. IF a User_Snippet produces a Parser_Error, THEN THE Backend SHALL return the Parser_Error as specified in Requirement 3, which is HTTP 422 with body {"error":"parser_error","line":N,"message":M}, where N is the 1-based line number and M is the message, and SHALL start no Simulation.
7. WHEN the Engine produces a Violation_Report and a Replayed_State for an accepted run request, THE Backend SHALL return HTTP 200 with a JSON object that has exactly two keys: "report", whose value is the Violation_Report text exactly as the Engine writer produced it, stored as a JSON string, and "replayed_state", whose value is the Replayed_State object defined in the Glossary or null. The Replayed_State is not placed inside the report, and the Violation_Report format does not change.
8. THE Backend SHALL make no LLM calls and no outbound network calls while it processes a run request.
9. THE Backend SHALL allow cross-origin requests only from the origins http://localhost:3000 and http://127.0.0.1:3000.
10. WHEN a GET /api/snippets request arrives, THE Backend SHALL return the four Demo_Snippet names and their C sources from `engine/demo.py`, in the order listed in Requirement 2.
11. WHEN a GET /api/status request arrives, THE Backend SHALL return the JSON object {"busy": true} while a Simulation is running and {"busy": false} otherwise.

### Requirement 7: Single simulation at a time and timeout

**User Story:** As a verification engineer, I want the Studio to refuse a second run while one is in progress and to stop runs that hang, so that the shared simulation build is never used by two runs at once and no run blocks the page.

#### Acceptance Criteria

1. WHILE a Simulation is running, THE Backend SHALL reject each new run request with HTTP 409 and body {"error":"busy"} and SHALL start no second Simulation.
2. Notwithstanding criterion 1 of this requirement, WHEN a run request contains a User_Snippet that the new entry point rejects with a Parser_Error while a Simulation is running, THE Backend SHALL return HTTP 422 with the parser_error body defined in Requirement 3, criterion 22 and SHALL NOT return HTTP 409. THE Backend SHALL run the new entry point and the size check of Requirement 3, criterion 25 before it checks for Busy_State, so a run request that fails either check while a Simulation is running receives the response of that check. A valid run request that arrives while a Simulation is running SHALL receive HTTP 409 under criterion 1 of this requirement.
3. WHEN a Simulation exits for any reason, including a normal end, a non-zero exit, or a stop under criterion 8, THE Backend SHALL accept the next valid run request and start a Simulation for it.
4. WHILE a run request sent by the Studio is pending or the most recent status response reports busy true, THE Studio SHALL disable Run_Control.
5. WHILE no run request sent by the Studio is pending and the most recent status response does not report busy true, THE Studio SHALL enable Run_Control.
6. WHILE the page is open, THE Studio SHALL send one GET /api/status request every 1 second.
7. WHEN the Backend returns HTTP 409, THE Studio SHALL display "A simulation is already running. Try again when it finishes." and SHALL show no results.
8. IF a Simulation runs longer than 60 seconds after the Backend starts it, THEN THE Backend SHALL stop the Simulation, return HTTP 504 with body {"error":"timeout"}, and return no Violation_Report.
9. WHEN the Studio receives HTTP 504, THE Studio SHALL display "The simulation ran longer than 60 seconds and was stopped. No partial results are shown." and SHALL show no results.
10. IF the Studio receives no HTTP response to a run request within 70 seconds after sending it, THEN THE Studio SHALL display "No response arrived within 70 seconds. The Backend may still be running the simulation. No results are shown." and SHALL show no results and no Recorded_Output.

### Requirement 8: Recorded snapshot fallback

**User Story:** As a verification engineer, I want the Demo_Snippet results to remain viewable when the Backend is down, with a clear label that they are recorded, so that I can review known results without mistaking them for a live run.

#### Acceptance Criteria

1. WHEN `python3 -m engine.demo run` replays all four Demo_Snippets and every replay completes without error, THE Engine SHALL write the Snapshot to `web/public/demo_snapshot.json` using the results of that same run.
2. THE Engine SHALL write the Snapshot as a JSON object with the keys created_utc and records.
3. THE Engine SHALL write the created_utc key as the UTC time at which the Engine writes the Snapshot, in ISO 8601 format ending in Z.
4. THE Engine SHALL write the records key as an array of four objects in the order listed in Requirement 2, where each object has the keys name, source, report, and replayed_state, name holds the Demo_Snippet name, source holds that Demo_Snippet's C source, and replayed_state holds the Replayed_State of that Demo_Snippet from the same run, or null.
5. THE Engine SHALL write the report value of each record as a JSON string that holds the Violation_Report text exactly as the Engine writer produced it for that Demo_Snippet in the same run, the same form as the report value in a Backend response under Requirement 6, criterion 7.
6. THE Studio SHALL parse the report value of each Snapshot record with the reader that Requirement 9, criterion 4 defines for the report string in a Backend response, and SHALL NOT use a separate reader for Recorded_Output.
7. IF any Demo_Snippet replay does not complete without error, THEN THE Engine SHALL write no Snapshot and leave the existing Snapshot file byte-for-byte unchanged.
8. THE Engine SHALL write the Snapshot only in the demo run path `python3 -m engine.demo run`, and no other Engine command or Backend code path SHALL write it.
9. THE Studio SHALL read Recorded_Output only from `web/public/demo_snapshot.json` and SHALL NOT read recorded data from any other file.
10. WHILE the most recent GET /api/status request has received no HTTP response within 2 seconds, THE Studio SHALL treat the Backend as an Unreachable_Backend.
11. IF the Backend is an Unreachable_Backend and the user runs a Demo_Snippet, THEN THE Studio SHALL display Recorded_Output for that Demo_Snippet, taken from the report and replayed_state of the Snapshot record whose name equals that Demo_Snippet name.
12. WHEN the Studio displays Recorded_Output, THE Studio SHALL label the source "Recorded output, created <time>", where <time> is the created_utc value of the Snapshot, copied exactly as stored.
13. WHILE Recorded_Output is displayed, THE Studio SHALL NOT display the word "live", in any letter case, in the source label or in any other text shown with the results.
14. IF the most recent GET /api/status request received an HTTP response, THEN THE Studio SHALL NOT display Recorded_Output for any run.
15. IF the Backend is an Unreachable_Backend and the user runs a User_Snippet, THEN THE Studio SHALL display "The backend is unreachable. User snippets need the backend." and SHALL NOT display Recorded_Output.
16. IF the Backend is an Unreachable_Backend, the user runs a Demo_Snippet, and the Snapshot file is missing, cannot be parsed as JSON, has no record with the keys name, source, report, and replayed_state for each of the four Demo_Snippet names, or has a record whose report value is not text that parses as an array of objects that match the Violation_Report schema in the Glossary, as Requirement 9, criterion 4 defines, THEN THE Studio SHALL display "The recorded output could not be loaded." and SHALL show no results.

### Requirement 9: Error states

**User Story:** As a verification engineer, I want each failure to show a specific message and no misleading results, so that I know whether a run failed, timed out, or was rejected.

#### Acceptance Criteria

1. IF the Backend is an Unreachable_Backend, THEN THE Studio SHALL apply the rules of Requirement 8, criteria 11 and 15.
2. THE Backend SHALL return HTTP 500 with body {"error":"simulation_failed","message":M} when a Simulation exits with a non-zero status, where M is one line that states the failure.
3. IF the Backend returns HTTP 500 with body {"error":"simulation_failed","message":M}, THEN THE Studio SHALL display "The simulation failed: " followed by M, and SHALL show no results and no Recorded_Output.
4. IF the response body of a run request is not valid JSON, or is not a JSON object with exactly the keys report and replayed_state, or its report value is not text that parses as an array of objects that match the Violation_Report schema in the Glossary, or its replayed_state value is neither null nor an object with the keys register, pre, and post, THEN THE Studio SHALL display "The backend returned a response the Studio cannot read. No results are shown." and SHALL show no results.
5. IF the Backend returns an HTTP status code other than 200, 400, 409, 422, 500, or 504, THEN THE Studio SHALL display "The backend returned an unexpected status " followed by the status code, and SHALL show no results.
6. IF a run request returns any error response, THEN THE Studio SHALL NOT display Recorded_Output for that run.
7. WHEN a run starts, THE Studio SHALL clear the Violation_List, the Register_Array values, and the source label from the previous run before it displays the new state.
8. IF the Backend returns HTTP 400 with body {"error":"too_large"}, THEN THE Studio SHALL display "The snippet is larger than 200 lines or 8 KB and was not run." and SHALL show no results.
9. IF the Backend returns HTTP 400 with body {"error":"invalid_request"}, THEN THE Studio SHALL display "The backend rejected the run request. No results are shown." and SHALL show no results.
10. IF the Backend returns HTTP 409 with body {"error":"busy"}, THEN THE Studio SHALL display the message defined in Requirement 7, criterion 7, and SHALL show no results.
11. IF the Backend returns HTTP 504 with body {"error":"timeout"}, THEN THE Studio SHALL display the message defined in Requirement 7, criterion 9, and SHALL show no results.
12. IF the Backend returns HTTP 422 with body {"error":"parser_error"} that carries the line number and message of a Parser_Error, THEN THE Studio SHALL display the Parser_Error as Requirement 3, criterion 23 specifies, and SHALL show no Violation_List rows and no Register_Array values.
13. IF the Backend returns HTTP 500 with a body other than {"error":"simulation_failed","message":M}, THEN THE Studio SHALL display the message defined in criterion 4 and SHALL show no results.

### Requirement 10: Wording and claims

**User Story:** As a verification engineer, I want the page to state the tool's limits in plain words and to avoid overstated claims, so that I do not read a replay as proof or as a whole-chip simulation.

#### Acceptance Criteria

1. WHILE the Studio is open, THE Studio SHALL display the text "RegSpectre replays register accesses on the uart_ctrl RTL block in Icarus Verilog. It does not simulate the whole chip."
2. WHILE the Studio is open, THE Studio SHALL display the text "Cycle numbers count rising clock edges in the uart_ctrl simulation. They are not timing measurements of a physical device."
3. WHILE the Studio is open, THE Studio SHALL display the text "RegSpectre replays a small C subset. It is not a full C compiler."
4. WHILE the Studio is open, THE Studio SHALL display the text "When hardware sets a bit on the same clock edge as the commit, the detector reports nothing."
5. WHILE the Studio is open, THE Studio SHALL display the text "Results cover only the snippet that was replayed. They do not prove that the UART_Core is correct."
6. THE Studio SHALL NOT display any text that states that RegSpectre is the first tool of its kind.
7. THE Studio SHALL NOT display any text that states that RegSpectre performs cycle-accurate simulation of a whole chip.
8. THE Studio SHALL NOT display any text that states that Hypothesis, a property-based test, or any other test proves the correctness of the UART_Core or of any register.
9. WHILE Recorded_Output, a Live_Result, an error message defined in Requirement 3, 7, 8, or 9, or no results are displayed, THE Studio SHALL keep the disclaimers of criteria 1 to 5 rendered on the page and not hidden, collapsed, or covered by another element.
10. WHILE Replayed_State is displayed, THE Studio SHALL display the text "Replayed state is the state of the replayed snippet in the uart_ctrl simulation. It is not the state of a whole chip."
11. WHILE Replayed_State is displayed, THE Studio SHALL display the text "Hardware noise that arrives between the pre sample and the commit is not in pre."
