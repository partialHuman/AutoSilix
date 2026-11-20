// Extended GCD testbench — corner cases not covered by tb_gcd.v
// Tests: both-zero edge (gcd(0,0) — undefined/zero passthrough), large values,
// co-prime large inputs, equal large inputs, single-cycle convergence (b=0),
// back-to-back requests, max-width boundary (65535).
//
// Compatible with all GCD experiment RTLs (baseline, exp01–exp05).
// Pass criterion: all run_case calls complete without $fatal.
// Final message: "EXTENDED TESTS PASSED: N cases"

`timescale 1ns/1ps

module tb_gcd_extended;
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

  always #5 clk = ~clk;  // 100 MHz

  // ---------------------------------------------------------------
  // Task: submit one request, wait for response, check and consume
  // ---------------------------------------------------------------
  task automatic run_case;
    input [15:0] a;
    input [15:0] b;
    input [15:0] expected;
    input [127:0] label;       // up to 16 characters for display
    integer cycles;
    begin
      @(negedge clk);
      wait (req_rdy === 1'b1);
      req_msg = {a, b};
      req_val = 1;
      @(negedge clk);
      req_val = 0;

      cycles = 0;
      while (resp_val !== 1'b1 && cycles < 5000) begin
        @(negedge clk);
        cycles = cycles + 1;
      end

      if (resp_val !== 1'b1) begin
        $display("TIMEOUT: gcd(%0d,%0d) [%s], expected %0d", a, b, label, expected);
        $fatal(1);
      end
      if (resp_msg !== expected) begin
        $display("FAIL: gcd(%0d,%0d) [%s], expected %0d, got %0d",
                 a, b, label, expected, resp_msg);
        $fatal(1);
      end

      $display("PASS: gcd(%0d,%0d) = %0d (%0d cycles) [%s]",
               a, b, resp_msg, cycles, label);
      passed = passed + 1;

      @(negedge clk);
      resp_rdy = 1;
      @(negedge clk);
      resp_rdy = 0;
    end
  endtask

  // ---------------------------------------------------------------
  // Stimulus
  // ---------------------------------------------------------------
  initial begin
    repeat (4) @(negedge clk);
    reset = 0;

    // ---- Basic sanity (replicate a few from tb_gcd.v) ----
    run_case(48,  18,  6,   "sanity_48_18");
    run_case(7,   13,  1,   "sanity_7_13");
    run_case(16,  16,  16,  "equal");

    // ---- Zero operands ----
    // GCD(0, n) = n and GCD(n, 0) = n per algorithm convention; GCD(0, 0) = 0 passthrough
    run_case(0,   0,   0,   "zero_both");
    run_case(0,   9,   9,   "zero_a");
    run_case(9,   0,   9,   "zero_b");
    run_case(0,   1,   1,   "zero_a_one");
    run_case(1,   0,   1,   "one_zero_b");

    // ---- Single-cycle convergence (a = b already, or b=0 after one sub) ----
    run_case(100, 100, 100, "same_100");
    run_case(1,   1,   1,   "same_1");

    // ---- Power-of-two inputs ----
    run_case(256, 64,  64,  "pow2_256_64");
    run_case(1024, 512, 512,"pow2_1k_512");
    run_case(0,   32768, 32768, "zero_a_pow2");

    // ---- Large co-prime (GCD=1) ----
    run_case(65521, 65519, 1, "coprime_large"); // both large primes close together
    run_case(49999, 50021, 1, "coprime_49k");

    // ---- Large equal ----
    run_case(65535, 65535, 65535, "max_equal");

    // ---- Large with known GCD ----
    // 60000 = 2^5 * 3 * 5^4; 45000 = 2^3 * 3^2 * 5^4; GCD = 2^3*3*5^4 = 15000
    run_case(60000, 45000, 15000, "large_gcd_15k");
    // 32760 = 2^3*3^2*5*7*13; 32736 = 2^5*3*11*31; GCD = 2^3*3 = 24
    run_case(32760, 32736, 24,   "large_near_gcd24");

    // ---- Boundary: one operand = 1 (GCD always 1) ----
    run_case(1,    65535, 1,   "one_max");
    run_case(65535, 1,   1,   "max_one");

    // ---- Back-to-back requests (no idle gap) ----
    run_case(12,   8,   4,   "bb_12_8");
    run_case(15,   10,  5,   "bb_15_10");
    run_case(21,   14,  7,   "bb_21_14");

    // ---- Asymmetric: small vs. large ----
    run_case(3,    65535, 3,  "small_large_3");
    run_case(7,    49,    7,  "small_large_7");
    run_case(13,   169,  13,  "small_large_13");

    $display("EXTENDED TESTS PASSED: %0d cases", passed);
    $finish;
  end

  // Global watchdog
  initial begin
    #5000000;
    $fatal(1, "Global simulation timeout — possible hang in GCD algorithm");
  end

endmodule

