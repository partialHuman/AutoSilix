// ==============================================================================
// Testbench: tb_alu_accumulator
// Description: Self-checking testbench for 8-bit ALU with accumulator.
// ==============================================================================

`timescale 1ns / 1ps

module tb_alu_accumulator;

    reg        clk;
    reg        rst_n;
    reg  [2:0] opcode;
    reg  [7:0] operand_b;
    reg        enable;
    wire [7:0] acc_out;
    wire       zero_flag;
    wire       carry_flag;
    wire       overflow_flag;

    integer errors = 0;
    integer tests_run = 0;

    alu_accumulator dut (
        .clk(clk),
        .rst_n(rst_n),
        .opcode(opcode),
        .operand_b(operand_b),
        .enable(enable),
        .acc_out(acc_out),
        .zero_flag(zero_flag),
        .carry_flag(carry_flag),
        .overflow_flag(overflow_flag)
    );

    always #5 clk = ~clk;

    task apply_op(
        input [2:0] op,
        input [7:0] op_b,
        input [7:0] exp_acc,
        input       exp_z,
        input       exp_c,
        input       exp_ovf
    );
        begin
            @(negedge clk);
            opcode    = op;
            operand_b = op_b;
            enable    = 1'b1;
            @(posedge clk);
            #1;
            tests_run = tests_run + 1;
            if (acc_out !== exp_acc) begin
                $display("[ERROR] %0t ns Op %b: Expected acc=%h, got %h", $time, op, exp_acc, acc_out);
                errors = errors + 1;
            end
            if (zero_flag !== exp_z) begin
                $display("[ERROR] %0t ns Op %b: Expected zero=%b, got %b", $time, op, exp_z, zero_flag);
                errors = errors + 1;
            end
            if (carry_flag !== exp_c) begin
                $display("[ERROR] %0t ns Op %b: Expected carry=%b, got %b", $time, op, exp_c, carry_flag);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        clk = 0;
        rst_n = 0;
        opcode = 0;
        operand_b = 0;
        enable = 0;

        #15;
        rst_n = 1;
        @(posedge clk);
        #1;

        // LOAD 0x42
        apply_op(3'b001, 8'h42, 8'h42, 1'b0, 1'b0, 1'b0);

        // ADD 0x10 -> 0x52
        apply_op(3'b010, 8'h10, 8'h52, 1'b0, 1'b0, 1'b0);

        // SUB 0x52 -> 0x00 (zero flag should be set)
        apply_op(3'b011, 8'h52, 8'h00, 1'b1, 1'b0, 1'b0);

        // LOAD 0xFF
        apply_op(3'b001, 8'hFF, 8'hFF, 1'b0, 1'b0, 1'b0);

        // ADD 0x01 -> 0x00 with carry!
        apply_op(3'b010, 8'h01, 8'h00, 1'b1, 1'b1, 1'b0);

        // AND with 0x0F
        apply_op(3'b001, 8'hAA, 8'hAA, 1'b0, 1'b0, 1'b0);
        apply_op(3'b100, 8'h55, 8'h00, 1'b1, 1'b0, 1'b0);

        // OR with 0xF0
        apply_op(3'b101, 8'hF0, 8'hF0, 1'b0, 1'b0, 1'b0);

        // XOR with 0xFF -> 0x0F
        apply_op(3'b110, 8'hFF, 8'h0F, 1'b0, 1'b0, 1'b0);

        // NOT -> 0xF0
        apply_op(3'b111, 8'h00, 8'hF0, 1'b0, 1'b0, 1'b0);

        $display("ALU Test completed: %0d tests, %0d errors", tests_run, errors);
        if (errors == 0) begin
            $display("TEST PASSED: ALU Accumulator verified.");
            $finish(0);
        end else begin
            $display("TEST FAILED: ALU Accumulator failed.");
            $finish(1);
        end
    end

endmodule
