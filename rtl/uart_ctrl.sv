module uart_ctrl(
  input  wire        clk,
  input  wire        rst_n,
  // Bus_Interface
  input  wire        we,        // write enable
  input  wire        re,        // read enable
  input  wire [31:0] addr,      // full byte address
  input  wire [31:0] wdata,
  output reg  [31:0] rdata,
  // Hardware inputs
  input  wire [3:0]  hw_set,    // bit i sets interrupt bit i
  input  wire        rx_valid,
  input  wire [7:0]  rx_data
);

reg [3:0] isr;   // UART_ISR bits 3:0
reg [7:0] rdr;   // UART_RDR bits 7:0

localparam [31:0] ISR_ADDR = 32'h40001004;
localparam [31:0] RDR_ADDR = 32'h40001008;
wire sel_isr = (addr == ISR_ADDR);
wire sel_rdr = (addr == RDR_ADDR);

// Combinational read data (read returns current value; side effects land on the clock edge)
always @(*) begin
  if (sel_isr)      rdata = {28'b0, isr};
  else if (sel_rdr) rdata = {24'b0, rdr};
  else              rdata = 32'b0;
end

// W1C clear applies only to writable bits 0,2,3 (mask 4'b1101); bit 1 (RX_READY) excluded.
wire [3:0] clear_mask = (we & sel_isr) ? (wdata[3:0] & 4'b1101) : 4'b0000;

// RDR read clears RX_READY (bit 1): rdr_clear_mask has bit 1 = rdr_read.
wire rdr_read  = re & sel_rdr;
wire [3:0] rdr_clear_mask = {2'b00, rdr_read, 1'b0};

// Hardware set: bit 0 TX_DONE, bit 1 RX_READY (rx_valid), bit 2 PARITY_ERR, bit 3 OVERRUN_ERR.
// OVERRUN_ERR also set on overrun (rx_valid while RX_READY set and RDR not being read).
wire overrun   = rx_valid & isr[1] & ~rdr_read;   // see Design Decision (a)/(b)
wire [3:0] hwset_mask = { hw_set[3] | overrun, hw_set[2], rx_valid, hw_set[0] };

// hw_set wins over W1C clear and RDR-read clear: OR applied after both clears (Requirement 1.7).
wire [3:0] isr_next = (isr & ~clear_mask & ~rdr_clear_mask) | hwset_mask;

// rx_valid loads new rx_data; RDR read clears to 0. Read + rx_valid in same cycle: rx_valid wins.
wire [7:0] rdr_next = rx_valid ? rx_data : (rdr_read ? 8'd0 : rdr);

// Clocked update + reset (Requirement 1.5 zeroes both on rst_n low)
always @(posedge clk or negedge rst_n) begin
  if (!rst_n) begin
    isr <= 4'd0;
    rdr <= 8'd0;
  end else begin
    isr <= isr_next;
    rdr <= rdr_next;
  end
end

endmodule