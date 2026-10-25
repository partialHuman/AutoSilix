// ==============================================================================
// Design: sequence_detector
// Module: sequence_detector
// Description: Overlapping sequence detector for bit pattern '1011'.
//              Synchronous on posedge clk, asynchronous active-low reset rst_n.
//              seq_detected goes high for 1 cycle upon receiving the 4th bit.
// ==============================================================================

`timescale 1ns / 1ps

module sequence_detector (
    input  wire clk,
    input  wire rst_n,
    input  wire data_in,
    output reg  seq_detected
);

    // State encoding (One-hot or binary)
    // S_IDLE: No matching bits
    // S_1:    Matched '1'
    // S_10:   Matched '10'
    // S_101:  Matched '101'
    localparam [1:0] S_IDLE = 2'b00;
    localparam [1:0] S_1    = 2'b01;
    localparam [1:0] S_10   = 2'b10;
    localparam [1:0] S_101  = 2'b11;

    reg [1:0] current_state, next_state;

    // Sequential state register
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            current_state <= S_IDLE;
        end else begin
            current_state <= next_state;
        end
    end

    // Next-state combinational logic
    always @(*) begin
        next_state = current_state;
        case (current_state)
            S_IDLE: begin
                if (data_in)
                    next_state = S_1;
                else
                    next_state = S_IDLE;
            end

            S_1: begin
                if (!data_in)
                    next_state = S_10;
                else
                    next_state = S_1; // stay in S_1 on consecutive 1s
            end

            S_10: begin
                if (data_in)
                    next_state = S_101;
                else
                    next_state = S_IDLE;
            end

            S_101: begin
                if (data_in)
                    // Detected '1011'! Overlapping detection:
                    // The last '1' matches the first '1' of the next sequence.
                    next_state = S_1;
                else
                    // '1010' -> prefix '10' is matched!
                    next_state = S_10;
            end

            default: next_state = S_IDLE;
        endcase
    end

    // Output logic (registered / Mealy-Moore consideration)
    // Moore output or synchronous output:
    // When in state S_101 and data_in is 1, the 4th bit is verified.
    // To ensure clean synchronous output registered on clock:
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            seq_detected <= 1'b0;
        end else begin
            if (current_state == S_101 && data_in == 1'b1) begin
                seq_detected <= 1'b1;
            end else begin
                seq_detected <= 1'b0;
            end
        end
    end

endmodule
