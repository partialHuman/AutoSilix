`timescale 1ns/1ps

module tb_unified_sub_equiv;
  reg  [15:0] in0;
  reg  [15:0] in1;
  wire [15:0] out;
  wire [0:0]  lt;

  reg clk = 0;
  reg reset = 0;
  integer errors = 0;
  integer tests = 0;
  integer i, j;

  // Instantiate the unified Subtractor from exp03
  Subtractor_0x422b1f52edd46a85 dut (
    .clk(clk),
    .reset(reset),
    .in0(in0),
    .in1(in1),
    .out(out),
    .lt(lt)
  );

  wire [15:0] gold_sub = in0 - in1;
  wire        gold_lt  = (in0 < in1);

  task check_pair;
    input [15:0] a, b;
    begin
      in0 = a;
      in1 = b;
      #1;
      tests = tests + 1;
      if (lt !== gold_lt) begin
        $display("[ERROR LT] a=%h (%0d), b=%h (%0d) -> got lt=%b, expected %b",
                 a, a, b, b, lt, gold_lt);
        errors = errors + 1;
      end
      if (out !== gold_sub) begin
        $display("[ERROR SUB] a=%h (%0d), b=%h (%0d) -> got out=%h, expected %h",
                 a, a, b, b, out, gold_sub);
        errors = errors + 1;
      end
    end
  endtask

  reg [15:0] edge_vals [0:15];

  initial begin
    $display("=== Starting Unified Comparator-Subtractor Equivalence Test ===");

    // Define comprehensive edge values
    edge_vals[0]  = 16'h0000;
    edge_vals[1]  = 16'h0001;
    edge_vals[2]  = 16'h0002;
    edge_vals[3]  = 16'h000F;
    edge_vals[4]  = 16'h007F;
    edge_vals[5]  = 16'h0080;
    edge_vals[6]  = 16'h00FF;
    edge_vals[7]  = 16'h0100;
    edge_vals[8]  = 16'h7FFE;
    edge_vals[9]  = 16'h7FFF;
    edge_vals[10] = 16'h8000;
    edge_vals[11] = 16'h8001;
    edge_vals[12] = 16'hFFFE;
    edge_vals[13] = 16'hFFFF;
    edge_vals[14] = 16'h5555;
    edge_vals[15] = 16'hAAAA;

    // 1. Exhaustive cross-product of all edge values (16x16 = 256 pairs)
    $display("1. Testing edge values cross-product...");
    for (i = 0; i < 16; i = i + 1) begin
      for (j = 0; j < 16; j = j + 1) begin
        check_pair(edge_vals[i], edge_vals[j]);
      end
    end

    // 2. Specific directed edge cases explicitly required by specification
    $display("2. Testing directed boundary cases...");
    check_pair(16'd0, 16'd0);           // 0 < 0
    check_pair(16'd0, 16'd1);           // 0 < 1
    check_pair(16'd1, 16'd0);           // 1 < 0
    check_pair(16'hFFFF, 16'd0);        // 16'hFFFF < 0
    check_pair(16'd0, 16'hFFFF);        // 0 < 16'hFFFF
    check_pair(16'h7FFF, 16'h8000);     // MSB boundary
    check_pair(16'h8000, 16'h7FFF);
    check_pair(16'h8000, 16'h8000);
    check_pair(16'h8000, 16'h8001);
    check_pair(16'h8001, 16'h8000);

    // 3. Exhaustive lower 8-bit space (256x256 = 65,536 pairs)
    $display("3. Exhaustive test across [0..255] x [0..255] (65,536 pairs)...");
    for (i = 0; i < 256; i = i + 1) begin
      for (j = 0; j < 256; j = j + 1) begin
        check_pair(i[15:0], j[15:0]);
      end
    end

    // 4. Randomized testing across full 16-bit space (100,000 random vectors)
    $display("4. Randomized testing across full 16-bit space (100,000 vectors)...");
    for (i = 0; i < 100000; i = i + 1) begin
      check_pair($urandom & 16'hFFFF, $urandom & 16'hFFFF);
    end

    $display("=================================================");
    $display("Equivalence Results:");
    $display("Total tests executed: %0d", tests);
    $display("Total errors:         %0d", errors);
    $display("Coverage: Edge cases + exhaustive 8-bit space + 100k random pairs");
    $display("=================================================");

    if (errors == 0) begin
      $display("PASS: Unified comparator-subtractor equivalence verified.");
      $finish(0);
    end else begin
      $display("FAIL: Unified comparator-subtractor equivalence failed!");
      $fatal(1);
    end
  end
endmodule

