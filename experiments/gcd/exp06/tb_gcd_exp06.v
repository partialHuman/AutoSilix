//-----------------------------------------------------------------------------
// AutoSilix Experiment 06 — Self-checking Verilog Testbench
//-----------------------------------------------------------------------------
// Compile/run (Icarus Verilog):
//   iverilog -g2012 -s tb_gcd_exp06 -o sim_exp06.vvp gcd.v tb_gcd_exp06.v && vvp sim_exp06.vvp
//
// Reference model: Euclid-by-modulo (golden_gcd).  It is independent of the DUT's
// subtractive algorithm.  Directed expected values are hand-derived literals.
// The subtractive step counter (golden_steps) is used ONLY for the latency check.
//
// A continuous monitor/scoreboard (always @(posedge clk)) runs during EVERY test and
// checks, each cycle:
//   * req_rdy and resp_val are never both high; neither is X after reset
//   * a pending response (resp_val=1, resp_rdy=0) stays asserted with unchanged data
//   * after an accepted request:   req_rdy=0, resp_val=0
//   * after a response handshake:  resp_val=0, req_rdy=1
//   * req_rdy does not drop without a request; reset returns the unit to idle
//   * no request is accepted while another is outstanding (no double acceptance)
//   * every accepted request yields exactly one response with correct data
//   * first resp_val appears exactly 2*n+2 cycles after the accept cycle
//     (n = number of subtract/swap steps)
//
// Test sections (counts are printed at the end):
//   1. Directed          26 cases (same list/order as verify_exp06.py DIRECTED_CASES)
//   2. Backpressure       6 cases, resp_rdy held low 40 cycles, req_val held high
//                         with a different message (must be ignored)
//   3. Chained            6 pairs, second request presented while first is in flight;
//                         accepted exactly one cycle after the first response handshake
//   4. Reset            every cycle offset of 5 transactions (incl. while the response
//                         is pending), 1- and 2-cycle resets, reset coinciding with a
//                         request, reset coinciding with resp_rdy; fresh transaction
//                         after each reset
//   5. Boundary         12x12 cross product of boundary operands (resp_rdy held high early)
//   6. Random         1000 vectors, random operand widths, random start delay,
//                         random resp_rdy delay / early resp_rdy, random decoy req_val
//-----------------------------------------------------------------------------

`timescale 1ns/1ps

module tb_gcd_exp06;
  localparam integer CYCLE_CAP = 300000; // worst case gcd(1,65535) needs 131,075 cycles
  localparam integer N_RANDOM  = 1000;

  reg clk = 0;
  reg [31:0] req_msg = 0;
  reg req_val = 0;
  reg reset = 1;
  reg resp_rdy = 0;

  wire req_rdy;
  wire [15:0] resp_msg;
  wire resp_val;

  integer passed_directed = 0;
  integer passed_backpressure = 0;
  integer passed_chained = 0;
  integer passed_reset = 0;
  integer passed_boundary = 0;
  integer passed_random = 0;

  gcd dut (
    .clk(clk),
    .req_msg(req_msg),
    .req_rdy(req_rdy),
    .req_val(req_val),
    .reset(reset),
    .resp_msg(resp_msg),
    .resp_rdy(resp_rdy),
    .resp_val(resp_val)
  );

  always #5 clk = ~clk; // 100 MHz simulation clock (functional only)

  //---------------------------------------------------------------------------
  // Failure helper
  //---------------------------------------------------------------------------
  integer cycle_count = 0;

  task automatic fail;
    input [511:0] msg;
    begin
      $display("[FAIL] t=%0t cycle=%0d: %0s", $time, cycle_count, msg);
      $fatal(1);
    end
  endtask

  //---------------------------------------------------------------------------
  // Reference functions
  //---------------------------------------------------------------------------
  // Euclid by modulo: independent of the RTL's subtractive algorithm.
  function automatic [15:0] golden_gcd;
    input [15:0] in_a;
    input [15:0] in_b;
    reg [15:0] a;
    reg [15:0] b;
    reg [15:0] t;
    begin
      a = in_a;
      b = in_b;
      while (b != 0) begin
        t = b;
        b = a % b;
        a = t;
      end
      golden_gcd = a;
    end
  endfunction

  // Number of subtract/swap steps of the subtractive algorithm (latency model only).
  function automatic integer golden_steps;
    input [15:0] in_a;
    input [15:0] in_b;
    reg [15:0] a;
    reg [15:0] b;
    reg [15:0] t;
    integer k;
    begin
      a = in_a;
      b = in_b;
      k = 0;
      while (b != 0) begin
        if (a < b) begin
          t = a;
          a = b;
          b = t;
        end else begin
          a = a - b;
        end
        k = k + 1;
      end
      golden_steps = k;
    end
  endfunction

  //---------------------------------------------------------------------------
  // Continuous protocol monitor + scoreboard
  // Samples pre-edge values at every posedge (DUT outputs are registered and updated
  // by non-blocking assignments, so reads here always see the previous cycle's state).
  //---------------------------------------------------------------------------
  reg        armed = 0;            // no checks until the first reset edge has been applied
  reg        m_valid = 0;
  reg        m_reset = 0;
  reg        m_req_val = 0;
  reg        m_req_rdy = 0;
  reg        m_resp_rdy = 0;
  reg        m_resp_val = 0;
  reg [15:0] m_resp_msg = 0;

  integer    outstanding = 0;
  reg        awaiting_first_resp = 0;
  reg [15:0] sb_expected = 0;
  integer    expected_steps = 0;
  integer    accept_cycle = 0;

  integer    n_accept = 0;
  integer    n_resp = 0;
  integer    n_latency = 0;
  integer    n_stable = 0;
  integer    n_reset_cycles = 0;

  always @(posedge clk) begin
    cycle_count = cycle_count + 1;

    if (armed) begin
      if ((^{req_rdy, resp_val}) === 1'bx)
        fail("X on req_rdy/resp_val after reset");
      if (req_rdy === 1'b1 && resp_val === 1'b1)
        fail("req_rdy and resp_val both asserted");

      if (m_valid) begin
        if (!m_reset && m_resp_val && !m_resp_rdy) begin
          if (resp_val !== 1'b1 || resp_msg !== m_resp_msg)
            fail("response dropped or changed while resp_rdy was low");
          n_stable = n_stable + 1;
        end
        if (m_reset) begin
          if (req_rdy !== 1'b1 || resp_val !== 1'b0)
            fail("unit not idle after reset");
        end
        if (!m_reset && m_req_val && m_req_rdy) begin
          if (req_rdy !== 1'b0 || resp_val !== 1'b0)
            fail("after request accept expected req_rdy=0 and resp_val=0");
        end
        if (!m_reset && m_resp_val && m_resp_rdy) begin
          if (resp_val !== 1'b0 || req_rdy !== 1'b1)
            fail("after response handshake expected resp_val=0 and req_rdy=1");
        end
        if (!m_reset && m_req_rdy && !m_req_val) begin
          if (req_rdy !== 1'b1)
            fail("req_rdy dropped without a request");
        end
      end

      if (reset) begin
        outstanding = 0;
        awaiting_first_resp = 0;
        n_reset_cycles = n_reset_cycles + 1;
      end else begin
        if (awaiting_first_resp && resp_val === 1'b1) begin
          if (cycle_count != accept_cycle + 2 * expected_steps + 2)
            fail("latency differs from 2*n+2 cycles");
          if (resp_msg !== sb_expected)
            fail("response data mismatch at first resp_val");
          awaiting_first_resp = 0;
          n_latency = n_latency + 1;
        end
        if (req_val && req_rdy === 1'b1) begin
          if (outstanding != 0)
            fail("request accepted while another transaction is outstanding");
          sb_expected = golden_gcd(req_msg[31:16], req_msg[15:0]);
          expected_steps = golden_steps(req_msg[31:16], req_msg[15:0]);
          outstanding = 1;
          awaiting_first_resp = 1;
          accept_cycle = cycle_count;
          n_accept = n_accept + 1;
        end
        if (resp_val === 1'b1 && resp_rdy) begin
          if (outstanding != 1)
            fail("response handshake with no outstanding request");
          if (resp_msg !== sb_expected)
            fail("response data mismatch at handshake");
          outstanding = 0;
          n_resp = n_resp + 1;
        end
      end
    end

    m_valid = armed;
    m_reset = reset;
    m_req_val = req_val;
    m_req_rdy = (req_rdy === 1'b1);
    m_resp_rdy = resp_rdy;
    m_resp_val = (resp_val === 1'b1);
    m_resp_msg = resp_msg;
    if (reset) armed = 1;
  end

  //---------------------------------------------------------------------------
  // Stimulus helpers (inputs are driven at negedge; the DUT samples at posedge)
  //---------------------------------------------------------------------------
  task automatic wait_req_rdy;
    integer waited;
    begin
      waited = 0;
      while (req_rdy !== 1'b1) begin
        @(negedge clk);
        waited = waited + 1;
        if (waited > CYCLE_CAP) fail("timeout waiting for req_rdy");
      end
    end
  endtask

  task automatic wait_resp_val;
    integer waited;
    begin
      waited = 0;
      while (resp_val !== 1'b1) begin
        @(negedge clk);
        waited = waited + 1;
        if (waited > CYCLE_CAP) fail("timeout waiting for resp_val");
      end
    end
  endtask

  // One full transaction.
  //   start_delay : idle cycles before the request is presented
  //   hold        : cycles resp_rdy stays low after resp_val is seen (backpressure)
  //   early       : 1 = resp_rdy is held high from the cycle of the request
  //   decoy       : 1 = req_val is held high with a different message while busy
  // While busy and not decoying, req_msg carries garbage with req_val low.
  task automatic send_and_get;
    input [15:0] a;
    input [15:0] b;
    input integer start_delay;
    input integer hold;
    input integer early;
    input integer decoy;
    output [15:0] got;
    integer i;
    reg [31:0] decoy_msg;
    begin
      decoy_msg = $random;
      repeat (start_delay) @(negedge clk);
      @(negedge clk);
      wait_req_rdy;
      req_msg = {a, b};
      req_val = 1;
      resp_rdy = (early != 0);
      @(negedge clk);                 // request was accepted at the posedge just passed
      req_msg = decoy_msg;
      req_val = (decoy != 0);
      wait_resp_val;
      got = resp_msg;
      if (early == 0) begin
        for (i = 0; i < hold; i = i + 1) begin
          @(negedge clk);             // resp_rdy still low
          if (resp_val !== 1'b1 || resp_msg !== got || req_rdy !== 1'b0)
            fail("response not held stable during backpressure");
        end
        resp_rdy = 1;
      end
      @(negedge clk);                 // response handshake happened at the posedge just passed
      resp_rdy = 0;
      req_val = 0;
      if (resp_val !== 1'b0 || req_rdy !== 1'b1)
        fail("unit not idle after response handshake");
    end
  endtask

  task automatic run_case_ex;
    input [15:0] a;
    input [15:0] b;
    input [15:0] expected;
    input [127:0] label;
    input integer start_delay;
    input integer hold;
    input integer early;
    input integer decoy;
    reg [15:0] got;
    begin
      send_and_get(a, b, start_delay, hold, early, decoy, got);
      if (got !== expected) begin
        $display("[FAIL] gcd(%0d,%0d) [%0s]: expected %0d, got %0d", a, b, label, expected, got);
        $fatal(1);
      end
      if (expected !== golden_gcd(a, b)) begin
        $display("[FAIL] testbench literal wrong: gcd(%0d,%0d) [%0s]", a, b, label);
        $fatal(1);
      end
    end
  endtask

  // Directed case with the default handshake (1 cycle of backpressure).
  task automatic run_case;
    input [15:0] a;
    input [15:0] b;
    input [15:0] expected;
    input [127:0] label;
    begin
      run_case_ex(a, b, expected, label, 0, 1, 0, 0);
      passed_directed = passed_directed + 1;
    end
  endtask

  // Second request B is presented (req_val held high) while A is still in flight.
  // It must not be accepted early, must not disturb A, and must be accepted exactly one
  // cycle after A's response handshake.
  task automatic run_chained;
    input [15:0] a1;
    input [15:0] b1;
    input [15:0] a2;
    input [15:0] b2;
    input integer hold;
    integer accepted_before;
    begin
      @(negedge clk);
      wait_req_rdy;
      req_msg = {a1, b1};
      req_val = 1;
      resp_rdy = 0;
      @(negedge clk);
      req_msg = {a2, b2};             // req_val stays high with request B
      wait_resp_val;
      if (resp_msg !== golden_gcd(a1, b1)) fail("chained: wrong result for first request");
      repeat (hold) @(negedge clk);
      accepted_before = n_accept;
      resp_rdy = 1;
      @(negedge clk);                 // response handshake; B's req_val was high but req_rdy low
      resp_rdy = 0;
      if (n_accept != accepted_before)
        fail("request accepted in the same cycle as the response handshake");
      if (req_rdy !== 1'b1 || resp_val !== 1'b0)
        fail("unit not ready the cycle after the response handshake");
      @(negedge clk);                 // held request B accepted at the posedge just passed
      if (n_accept != accepted_before + 1)
        fail("held request not accepted one cycle after the response handshake");
      req_val = 0;
      wait_resp_val;
      if (resp_msg !== golden_gcd(a2, b2)) fail("chained: wrong result for second request");
      resp_rdy = 1;
      @(negedge clk);
      resp_rdy = 0;
      passed_chained = passed_chained + 1;
    end
  endtask

  // Reset asserted `offset` cycles after a request is accepted (or earlier, as soon as the
  // response becomes valid, which covers reset while a response is pending).
  task automatic run_reset_at_offset;
    input [15:0] a;
    input [15:0] b;
    input integer offset;
    input integer width;
    integer i;
    reg [15:0] got;
    begin
      @(negedge clk);
      wait_req_rdy;
      req_msg = {a, b};
      req_val = 1;
      resp_rdy = 0;
      @(negedge clk);
      req_val = 0;
      i = 0;
      while (i < offset && resp_val !== 1'b1) begin
        @(negedge clk);
        i = i + 1;
      end
      reset = 1;
      repeat (width) @(negedge clk);
      reset = 0;
      if (req_rdy !== 1'b1 || resp_val !== 1'b0)
        fail("unit not idle after mid-transaction reset");
      repeat (12) @(negedge clk);
      if (req_rdy !== 1'b1 || resp_val !== 1'b0)
        fail("ghost response or busy unit after reset");
      // A fresh transaction must be unaffected by whatever was in flight.
      send_and_get(16'd21, 16'd14, 0, 1, 0, 0, got);
      if (got !== 16'd7) fail("fresh transaction after reset returned a wrong result");
      passed_reset = passed_reset + 1;
    end
  endtask

  //---------------------------------------------------------------------------
  // Main stimulus
  //---------------------------------------------------------------------------
  integer i;
  integer j;
  integer k;
  integer span;
  reg [31:0] rv;
  reg [31:0] tv;
  reg [15:0] ra;
  reg [15:0] rb;
  reg [15:0] got_main;
  reg [15:0] bvals [0:11];
  reg [15:0] rst_a [0:4];
  reg [15:0] rst_b [0:4];

  initial begin
    bvals[0] = 0;      bvals[1] = 1;      bvals[2] = 2;      bvals[3] = 127;
    bvals[4] = 128;    bvals[5] = 255;    bvals[6] = 256;    bvals[7] = 257;
    bvals[8] = 32767;  bvals[9] = 32768;  bvals[10] = 65534; bvals[11] = 65535;
    rst_a[0] = 48;  rst_b[0] = 18;
    rst_a[1] = 7;   rst_b[1] = 13;
    rst_a[2] = 16;  rst_b[2] = 16;
    rst_a[3] = 9;   rst_b[3] = 0;
    rst_a[4] = 0;   rst_b[4] = 9;

    repeat (4) @(negedge clk);
    reset = 0;

    $display("=== AutoSilix Exp06 Verilog Testbench Started ===");

    // 1. Directed cases (26)
    run_case(48,    18,    6,     "sanity_48_18");
    run_case(7,     13,    1,     "sanity_7_13");
    run_case(16,    16,    16,    "equal_16");
    run_case(0,     9,     9,     "zero_a");
    run_case(9,     0,     9,     "zero_b");
    run_case(0,     0,     0,     "zero_both");
    run_case(0,     1,     1,     "zero_a_one");
    run_case(1,     0,     1,     "one_zero_b");
    run_case(100,   100,   100,   "same_100");
    run_case(1,     1,     1,     "same_1");
    run_case(256,   64,    64,    "pow2_256_64");
    run_case(1024,  512,   512,   "pow2_1k_512");
    run_case(0,     32768, 32768, "zero_a_pow2");
    run_case(65521, 65519, 1,     "coprime_large");
    run_case(49999, 50021, 1,     "coprime_49k");
    run_case(65535, 65535, 65535, "max_equal");
    run_case(60000, 45000, 15000, "large_gcd_15k");
    run_case(32760, 32736, 24,    "large_near_gcd24");
    run_case(1,     65535, 1,     "one_max");
    run_case(65535, 1,     1,     "max_one");
    run_case(12,    8,     4,     "bb_12_8");
    run_case(15,    10,    5,     "bb_15_10");
    run_case(21,    14,    7,     "bb_21_14");
    run_case(3,     65535, 3,     "small_large_3");
    run_case(7,     49,    7,     "small_large_7");
    run_case(13,    169,   13,    "small_large_13");
    $display("[PASS] Directed & corner cases complete: %0d cases", passed_directed);

    // 2. Backpressure: resp_rdy low for 40 cycles, req_val held high with a decoy message
    run_case_ex(48,    18,    6,     "bp_48_18",   0, 40, 0, 1);
    passed_backpressure = passed_backpressure + 1;
    run_case_ex(0,     0,     0,     "bp_zero",    0, 40, 0, 1);
    passed_backpressure = passed_backpressure + 1;
    run_case_ex(9,     0,     9,     "bp_9_0",     0, 40, 0, 1);
    passed_backpressure = passed_backpressure + 1;
    run_case_ex(0,     9,     9,     "bp_0_9",     0, 40, 0, 1);
    passed_backpressure = passed_backpressure + 1;
    run_case_ex(65535, 65535, 65535, "bp_max",     0, 40, 0, 1);
    passed_backpressure = passed_backpressure + 1;
    run_case_ex(65521, 65519, 1,     "bp_coprime", 0, 40, 0, 1);
    passed_backpressure = passed_backpressure + 1;
    $display("[PASS] Backpressure (40 cycles, req_val held high) complete: %0d cases",
             passed_backpressure);

    // 3. Chained requests with req_val held high
    run_chained(48,    18, 7,     13,    0);
    run_chained(9,     0,  0,     9,     3);
    run_chained(0,     0,  0,     0,     6);
    run_chained(16,    16, 100,   100,   9);
    run_chained(21,    14, 25,    15,    12);
    run_chained(65535, 1,  1,     65535, 15);
    $display("[PASS] Chained requests complete: %0d pairs", passed_chained);

    // 4. Reset at every cycle offset, 1- and 2-cycle resets
    for (k = 0; k < 5; k = k + 1) begin
      span = 2 * golden_steps(rst_a[k], rst_b[k]) + 6;
      for (i = 0; i <= span; i = i + 1) begin
        run_reset_at_offset(rst_a[k], rst_b[k], i, 1);
        run_reset_at_offset(rst_a[k], rst_b[k], i, 2);
      end
    end
    // Reset coinciding with a request: the request must be dropped.
    @(negedge clk);
    wait_req_rdy;
    req_msg = {16'd48, 16'd18};
    req_val = 1;
    reset = 1;
    @(negedge clk);
    req_val = 0;
    reset = 0;
    if (req_rdy !== 1'b1 || resp_val !== 1'b0) fail("reset coinciding with req_val: not idle");
    repeat (20) @(negedge clk);
    if (req_rdy !== 1'b1 || resp_val !== 1'b0) fail("request accepted during reset");
    passed_reset = passed_reset + 1;
    // Reset coinciding with the response handshake.
    @(negedge clk);
    wait_req_rdy;
    req_msg = {16'd48, 16'd18};
    req_val = 1;
    @(negedge clk);
    req_val = 0;
    wait_resp_val;
    reset = 1;
    resp_rdy = 1;
    @(negedge clk);
    reset = 0;
    resp_rdy = 0;
    if (req_rdy !== 1'b1 || resp_val !== 1'b0) fail("reset coinciding with resp_rdy: not idle");
    send_and_get(16'd30, 16'd12, 0, 0, 0, 0, got_main);
    if (got_main !== 16'd6) fail("transaction after reset+resp_rdy returned a wrong result");
    passed_reset = passed_reset + 1;
    $display("[PASS] Reset scenarios complete: %0d", passed_reset);

    // 5. Boundary cross product (resp_rdy held high early)
    for (i = 0; i < 12; i = i + 1) begin
      for (j = 0; j < 12; j = j + 1) begin
        send_and_get(bvals[i], bvals[j], 0, 0, 1, 0, got_main);
        if (got_main !== golden_gcd(bvals[i], bvals[j])) begin
          $display("[FAIL] boundary gcd(%0d,%0d): expected %0d, got %0d",
                   bvals[i], bvals[j], golden_gcd(bvals[i], bvals[j]), got_main);
          $fatal(1);
        end
        passed_boundary = passed_boundary + 1;
      end
    end
    $display("[PASS] Boundary cross product complete: %0d pairs", passed_boundary);

    // 6. Randomized operands and handshake timing
    $display("Running %0d randomized vectors with random handshake timing...", N_RANDOM);
    for (i = 0; i < N_RANDOM; i = i + 1) begin
      rv = $random;
      tv = $random;
      ra = rv[31:16];
      rb = rv[15:0];
      case (tv[18:16] % 5)
        0: begin ra = ra & 16'h00FF; rb = rb & 16'h00FF; end
        1: begin rb = rb & 16'h00FF; end
        2: begin ra = ra & 16'h00FF; end
        default: begin end
      endcase
      send_and_get(ra, rb, tv[1:0], tv[6:4] % 7, (tv[9:8] == 2'b00), (tv[12:11] == 2'b00),
                   got_main);
      if (got_main !== golden_gcd(ra, rb)) begin
        $display("[FAIL] Randomized gcd(%0d,%0d): expected %0d, got %0d",
                 ra, rb, golden_gcd(ra, rb), got_main);
        $fatal(1);
      end
      passed_random = passed_random + 1;
    end
    $display("[PASS] %0d randomized vectors complete with 0 errors", passed_random);

    @(negedge clk);
    if (outstanding != 0) fail("a transaction is still outstanding at the end of the test");

    $display("Monitor: %0d accepted, %0d responses, %0d latency checks, %0d stability checks, %0d reset cycles",
             n_accept, n_resp, n_latency, n_stable, n_reset_cycles);
    $display("=== ALL TESTS PASSED: %0d directed, %0d backpressure, %0d chained, %0d reset, %0d boundary, %0d random ===",
             passed_directed, passed_backpressure, passed_chained, passed_reset,
             passed_boundary, passed_random);
    $finish;
  end

  // Global watchdog (per-case timeouts normally fire first)
  initial begin
    #200000000;
    $fatal(1, "[ERROR] Global simulation watchdog timeout");
  end

endmodule
