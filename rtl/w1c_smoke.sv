module w1c_smoke(
  input  wire        clk,
  input  wire        rst_n,
  input  wire        we,
  input  wire [31:0] wdata,
  input  wire [31:0] hw_set,
  output reg  [31:0] status
);
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) status <= 32'd0;
    else        status <= (status & ~(we ? wdata : 32'd0)) | hw_set;
  end
endmodule
