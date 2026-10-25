// ==============================================================================
// Design: alu_accumulator
// Module: alu_accumulator
// Description: 8-bit Arithmetic Logic Unit with internal Accumulator register.
//              Operations:
//                000: NOP (hold accumulator)
//                001: LOAD (acc <= operand_b)
//                010: ADD  (acc <= acc + operand_b)
//                011: SUB  (acc <= acc - operand_b)
//                100: AND  (acc <= acc & operand_b)
//                101: OR   (acc <= acc | operand_b)
//                110: XOR  (acc <= acc ^ operand_b)
//                111: NOT  (acc <= ~acc)
//              Flags: zero, carry, overflow
// ==============================================================================

`timescale 1ns / 1ps

module alu_accumulator (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [2:0]  opcode,
    input  wire [7:0]  operand_b,
    input  wire        enable,
    output reg  [7:0]  acc_out,
    output reg         zero_flag,
    output reg         carry_flag,
    output reg         overflow_flag
);

    reg [8:0] alu_result;
    reg       ovf_calc;

    always @(*) begin
        alu_result = {1'b0, acc_out};
        ovf_calc   = 1'b0;

        case (opcode)
            3'b000: begin // NOP
                alu_result = {1'b0, acc_out};
            end
            3'b001: begin // LOAD
                alu_result = {1'b0, operand_b};
            end
            3'b010: begin // ADD
                alu_result = {1'b0, acc_out} + {1'b0, operand_b};
                // Overflow if same sign inputs produce different sign output
                ovf_calc = (~(acc_out[7] ^ operand_b[7])) & (acc_out[7] ^ alu_result[7]);
            end
            3'b011: begin // SUB
                alu_result = {1'b0, acc_out} - {1'b0, operand_b};
                // Overflow in subtraction
                ovf_calc = (acc_out[7] ^ operand_b[7]) & (acc_out[7] ^ alu_result[7]);
            end
            3'b100: begin // AND
                alu_result = {1'b0, acc_out & operand_b};
            end
            3'b101: begin // OR
                alu_result = {1'b0, acc_out | operand_b};
            end
            3'b110: begin // XOR
                alu_result = {1'b0, acc_out ^ operand_b};
            end
            3'b111: begin // NOT
                alu_result = {1'b0, ~acc_out};
            end
            default: alu_result = {1'b0, acc_out};
        endcase
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            acc_out       <= 8'h00;
            zero_flag     <= 1'b1;
            carry_flag    <= 1'b0;
            overflow_flag <= 1'b0;
        end else if (enable) begin
            acc_out       <= alu_result[7:0];
            zero_flag     <= (alu_result[7:0] == 8'h00);
            carry_flag    <= alu_result[8];
            overflow_flag <= ovf_calc;
        end
    end

endmodule
