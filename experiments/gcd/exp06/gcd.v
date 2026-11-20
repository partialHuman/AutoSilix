//-----------------------------------------------------------------------------
// AutoSilix Experiment 06 — 8-bit Split Pipelined GCD Architecture
//-----------------------------------------------------------------------------
// Top Module: gcd
// Clock constraint: 1.10 ns, SKY130HD. NOT timing-closed: measured detailed-
// placement result is WNS -1.26 ns / min period 2.36 ns (see README.md).
//
// Algorithm (subtractive GCD): while (b != 0) { if (a < b) swap(a, b); else
// a = a - b; }  Result = a_reg once b_reg == 0.  Latency from request accept to
// resp_val is 2*n + 2 clock edges, n = number of subtract/swap steps.
//
// Datapath split:
//  - STAGE1: diff_lo = a[7:0] - b[7:0], borrow_mid = (a[7:0] < b[7:0]); latched
//            into pipe_* registers.  If b == 0 the FSM goes to DONE instead.
//  - STAGE2: diff_hi = a_hi - b_hi - borrow_mid; borrow_final = (a < b) selects
//            swap or subtract write-back into a_reg / b_reg.
//  - resp_msg is driven directly from a_reg (not through the subtractor).
//
// Note: a_reg/b_reg do not change in STAGE1, so pipe_{a,b}_{hi,lo} equal the
// matching bytes of a_reg/b_reg in STAGE2 (functionally redundant; kept as-is
// pending a timing study, see README.md).  Yosys may re-encode the FSM one-hot.
// Handshake: req_rdy = (state == IDLE), resp_val = (state == DONE).
//-----------------------------------------------------------------------------

`timescale 1ns/1ps

module gcd
(
  input  wire        clk,
  input  wire [31:0] req_msg,
  output wire        req_rdy,
  input  wire        req_val,
  input  wire        reset,
  output wire [15:0] resp_msg,
  input  wire        resp_rdy,
  output wire        resp_val
);

  //---------------------------------------------------------------------------
  // FSM State Encoding
  //---------------------------------------------------------------------------
  localparam [1:0]
    STATE_IDLE   = 2'd0,
    STATE_STAGE1 = 2'd1,
    STATE_STAGE2 = 2'd2,
    STATE_DONE   = 2'd3;

  reg [1:0] state, next_state;

  //---------------------------------------------------------------------------
  // Datapath Registers
  //---------------------------------------------------------------------------
  reg [15:0] a_reg;
  reg [15:0] b_reg;

  // Pipeline Registers (Stage 1 -> Stage 2)
  reg [7:0]  pipe_diff_lo;
  reg        pipe_borrow_mid;
  reg [7:0]  pipe_a_hi;
  reg [7:0]  pipe_b_hi;
  reg [7:0]  pipe_a_lo;
  reg [7:0]  pipe_b_lo;

  // Control and status wires
  wire is_b_zero;
  assign is_b_zero = (b_reg == 16'd0);

  //---------------------------------------------------------------------------
  // Stage 1 Combinational Logic: 8-bit Low-Byte Subtraction & Borrow
  //---------------------------------------------------------------------------
  wire [7:0] diff_lo;
  wire       borrow_mid;

  assign diff_lo    = a_reg[7:0] - b_reg[7:0];
  assign borrow_mid = (a_reg[7:0] < b_reg[7:0]);

  //---------------------------------------------------------------------------
  // Stage 2 Combinational Logic: 8-bit High-Byte Subtraction & Borrow Propagate
  //---------------------------------------------------------------------------
  wire [8:0] sub_hi_extended;
  wire [7:0] diff_hi;
  wire       borrow_final;
  wire [15:0] sub_diff_full;

  // Subtraction with borrow-in: {1'b0, A_hi} - {1'b0, B_hi} - borrow_mid
  assign sub_hi_extended = {1'b0, pipe_a_hi} - {1'b0, pipe_b_hi} - {8'd0, pipe_borrow_mid};
  assign diff_hi         = sub_hi_extended[7:0];
  assign borrow_final    = sub_hi_extended[8]; // MSB indicates underflow (A < B)

  assign sub_diff_full   = {diff_hi, pipe_diff_lo};

  //---------------------------------------------------------------------------
  // FSM Next-State Logic
  //---------------------------------------------------------------------------
  always @(*) begin
    next_state = state;
    case (state)
      STATE_IDLE: begin
        if (req_val && req_rdy)
          next_state = STATE_STAGE1;
      end

      STATE_STAGE1: begin
        if (is_b_zero)
          next_state = STATE_DONE;
        else
          next_state = STATE_STAGE2;
      end

      STATE_STAGE2: begin
        // Stage 2 always commits writeback and loops back to Stage 1
        next_state = STATE_STAGE1;
      end

      STATE_DONE: begin
        if (resp_val && resp_rdy)
          next_state = STATE_IDLE;
      end

      default: next_state = STATE_IDLE;
    endcase
  end

  //---------------------------------------------------------------------------
  // FSM State & Datapath Sequential Logic
  //---------------------------------------------------------------------------
  always @(posedge clk) begin
    if (reset) begin
      state           <= STATE_IDLE;
      a_reg           <= 16'd0;
      b_reg           <= 16'd0;
      pipe_diff_lo    <= 8'd0;
      pipe_borrow_mid <= 1'b0;
      pipe_a_hi       <= 8'd0;
      pipe_b_hi       <= 8'd0;
      pipe_a_lo       <= 8'd0;
      pipe_b_lo       <= 8'd0;
    end else begin
      state <= next_state;

      case (state)
        STATE_IDLE: begin
          if (req_val && req_rdy) begin
            a_reg <= req_msg[31:16];
            b_reg <= req_msg[15:0];
          end
        end

        STATE_STAGE1: begin
          if (!is_b_zero) begin
            // Latch Stage 1 results into pipeline registers
            pipe_diff_lo    <= diff_lo;
            pipe_borrow_mid <= borrow_mid;
            pipe_a_hi       <= a_reg[15:8];
            pipe_b_hi       <= b_reg[15:8];
            pipe_a_lo       <= a_reg[7:0];
            pipe_b_lo       <= b_reg[7:0];
          end
        end

        STATE_STAGE2: begin
          // Stage 2 commit: swap if A < B, else subtract
          if (borrow_final) begin
            // A < B: Swap A and B
            a_reg <= {pipe_b_hi, pipe_b_lo};
            b_reg <= {pipe_a_hi, pipe_a_lo};
          end else begin
            // A >= B: A <= A - B, B holds steady
            a_reg <= sub_diff_full;
            b_reg <= {pipe_b_hi, pipe_b_lo};
          end
        end

        STATE_DONE: begin
          // Hold a_reg steady for resp_msg
        end

        default: begin
          a_reg <= a_reg;
          b_reg <= b_reg;
        end
      endcase
    end
  end

  //---------------------------------------------------------------------------
  // Output Assignments
  //---------------------------------------------------------------------------
  assign req_rdy  = (state == STATE_IDLE);
  assign resp_val = (state == STATE_DONE);

  // resp_msg is driven directly from a_reg (decoupled from the subtractor)
  assign resp_msg = a_reg;

endmodule
