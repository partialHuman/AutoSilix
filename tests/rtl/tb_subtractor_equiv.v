`timescale 1ns/1ps

module tb_subtractor_equiv;
  reg [15:0] in0;
  reg [15:0] in1;
  wire [15:0] out_ripple;
  wire [15:0] out_golden;

  reg clk = 0;
  reg reset = 0;
  integer errors = 0;
  integer tests = 0;
  integer i;

  // Instantiate the ripple-borrow subtractor from exp02
  Subtractor_0x422b1f52edd46a85 dut (
    .clk(clk),
    .reset(reset),
    .in0(in0),
    .in1(in1),
    .out(out_ripple)
  );

  // Golden model: direct 16-bit subtraction
  assign out_golden = in0 - in1;

  task check_sub;
    input [15:0] a, b;
    begin
      in0 = a;
      in1 = b;
      #1;
      tests = tests + 1;
      if (out_ripple !== out_golden) begin
        $display("ERROR at test %0d: in0=%h (%0d), in1=%h (%0d) -> ripple=%h, golden=%h",
                 tests, a, a, b, b, out_ripple, out_golden);
        errors = errors + 1;
      end
    end
  endtask

  initial begin
    $display("=== Starting Exhaustive / Edge-Case Subtractor Equivalence Check ===");

    // 1. Zeros and Identical values
    check_sub(16'h0000, 16'h0000);
    check_sub(16'hFFFF, 16'hFFFF);
    check_sub(16'hAAAA, 16'hAAAA);
    check_sub(16'h5555, 16'h5555);

    // 2. Full borrow propagation across all 16 bits
    check_sub(16'h0000, 16'h0001); // Wraparound borrow to 16'hFFFF
    check_sub(16'h8000, 16'h0001); // 16'h7FFF
    check_sub(16'h0001, 16'h0002); // Wraparound
    check_sub(16'h0000, 16'hFFFF);
    check_sub(16'h0001, 16'hFFFF);

    // 3. Bit-by-bit walk
    for (i = 0; i < 16; i = i + 1) begin
      check_sub(16'h0000, (1 << i));
      check_sub((1 << i), 16'h0000);
      check_sub((1 << i), (1 << i));
      check_sub(16'hFFFF, (1 << i));
    end

    // 4. Random coverage test (65536 cases)
    for (i = 0; i < 65536; i = i + 1) begin
      check_sub($urandom & 16'hFFFF, $urandom & 16'hFFFF);
    end

    $display("=== Subtractor Equivalence Results ===");
    $display("Tests executed: %0d", tests);
    $display("Errors found:   %0d", errors);

    if (errors == 0) begin
      $display("PASS: Subtractor combinational equivalence fully verified.");
      $finish(0);
    end else begin
      $display("FAIL: Subtractor combinational equivalence mismatch!");
      $fatal(1);
    end
  end
endmodule

