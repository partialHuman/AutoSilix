`timescale 1ns/1ps

module tb_gcd;
  reg clk = 0;
  reg [31:0] req_msg = 0;
  reg req_val = 0;
  reg reset = 1;
  reg resp_rdy = 0;

  wire req_rdy;
  wire [15:0] resp_msg;
  wire resp_val;
  integer passed = 0;

  gcd dut (
    .clk(clk), .req_msg(req_msg), .req_rdy(req_rdy),
    .req_val(req_val), .reset(reset), .resp_msg(resp_msg),
    .resp_rdy(resp_rdy), .resp_val(resp_val)
  );

  always #5 clk = ~clk;

  task run_case;
    input [15:0] a, b, expected;
    integer cycles;
    begin
      @(negedge clk);
      wait (req_rdy === 1'b1);
      req_msg = {a, b};
      req_val = 1;
      @(negedge clk);
      req_val = 0;

      cycles = 0;
      while (resp_val !== 1'b1 && cycles < 2000) begin
        @(negedge clk);
        cycles = cycles + 1;
      end

      if (resp_val !== 1'b1 || resp_msg !== expected) begin
        $display("FAIL: gcd(%0d,%0d), expected %0d, got %0d",
                 a, b, expected, resp_msg);
        $fatal(1);
      end

      $display("PASS: gcd(%0d,%0d) = %0d (%0d cycles)",
               a, b, resp_msg, cycles);
      passed = passed + 1;

      @(negedge clk);
      resp_rdy = 1;
      @(negedge clk);
      resp_rdy = 0;
    end
  endtask

  initial begin
    repeat (3) @(negedge clk);
    reset = 0;

    run_case(48, 18, 6);
    run_case(7, 13, 1);
    run_case(16, 16, 16);
    run_case(0, 9, 9);
    run_case(9, 0, 9);

    $display("PASS: %0d test cases completed", passed);
    $finish;
  end

  initial begin
    #50000;
    $fatal(1, "Global simulation timeout");
  end
endmodule
