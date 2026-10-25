// ==============================================================================
// Testbench: tb_sequence_detector
// Description: Comprehensive self-checking testbench for '1011' sequence detector.
//              Tests:
//              1. Asynchronous reset initialization and recovery
//              2. Direct sequence match (1011)
//              3. Overlapping sequence match (1011011)
//              4. Non-matching patterns (1010, 0000, 1111)
//              5. Reset during active sequence reception
//              6. Back-to-back repetitions (10111011)
// ==============================================================================

`timescale 1ns / 1ps

module tb_sequence_detector;

    reg clk;
    reg rst_n;
    reg data_in;
    wire seq_detected;

    integer errors = 0;
    integer tests_run = 0;

    // Instantiate DUT (Device Under Test)
    sequence_detector dut (
        .clk(clk),
        .rst_n(rst_n),
        .data_in(data_in),
        .seq_detected(seq_detected)
    );

    // Clock generation: 10 ns period (100 MHz)
    always #5 clk = ~clk;

    // Helper task to send one bit on posedge clk and check expected detection on NEXT cycle
    task send_bit(input bit_val, input expected_detect);
        begin
            @(negedge clk);
            data_in = bit_val;
            @(posedge clk);
            #1; // Sample shortly after posedge
            tests_run = tests_run + 1;
            if (seq_detected !== expected_detect) begin
                $display("[ERROR] Time %0t ns: Expected seq_detected=%b, got %b (data_in=%b)",
                         $time, expected_detect, seq_detected, bit_val);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        // VCD dump for waveform debugging
        $dumpfile("sequence_detector.vcd");
        $dumpvars(0, tb_sequence_detector);

        clk = 0;
        rst_n = 0;
        data_in = 0;

        $display("=== STARTING SEQUENCE DETECTOR TESTBENCH ===");

        // Test 1: Reset check
        #15;
        if (seq_detected !== 1'b0) begin
            $display("[ERROR] Reset failed: seq_detected is not 0 during reset");
            errors = errors + 1;
        end
        @(negedge clk);
        rst_n = 1; // Release reset
        @(posedge clk);
        #1;

        // Test 2: Standard match '1011'
        $display("--- Test 2: Standard sequence '1011' ---");
        send_bit(1'b1, 1'b0);
        send_bit(1'b0, 1'b0);
        send_bit(1'b1, 1'b0);
        send_bit(1'b1, 1'b1); // Detected here!

        // Test 3: Idle / non-detect follow up
        send_bit(1'b0, 1'b0);

        // Test 4: Overlapping match '1011011'
        // We already sent '0' (state S_10). Next '1' -> S_101. Next '1' -> S_1 (detected!)
        $display("--- Test 4: Overlapping sequence '1011011' continuation ---");
        send_bit(1'b1, 1'b0);
        send_bit(1'b1, 1'b1); // Second detection via overlap!

        // Test 5: Non-matching sequence '1010'
        $display("--- Test 5: Non-matching sequence '1010' ---");
        send_bit(1'b1, 1'b0);
        send_bit(1'b0, 1'b0);
        send_bit(1'b1, 1'b0);
        send_bit(1'b0, 1'b0); // S_101 + '0' -> S_10, no detection

        // Test 6: All zeros '0000'
        $display("--- Test 6: All zeros ---");
        send_bit(1'b0, 1'b0);
        send_bit(1'b0, 1'b0);
        send_bit(1'b0, 1'b0);
        send_bit(1'b0, 1'b0);

        // Test 7: All ones '11111'
        $display("--- Test 7: All ones ---");
        send_bit(1'b1, 1'b0);
        send_bit(1'b1, 1'b0);
        send_bit(1'b1, 1'b0);
        send_bit(1'b1, 1'b0);

        // Test 8: Reset during sequence
        $display("--- Test 8: Reset assertion during sequence ---");
        send_bit(1'b0, 1'b0);
        send_bit(1'b1, 1'b0);
        send_bit(1'b0, 1'b0); // Now in S_10
        @(negedge clk);
        rst_n = 0; // Async reset assertion
        #2;
        if (seq_detected !== 1'b0) begin
            $display("[ERROR] Asynchronous reset failed during sequence");
            errors = errors + 1;
        end
        #10;
        rst_n = 1;
        @(posedge clk);

        // After reset, sending '1' should go to S_1 (not S_101)
        send_bit(1'b1, 1'b0); // S_1
        send_bit(1'b1, 1'b0); // S_1, no false detect

        // Test 9: Clean detection after reset recovery
        $display("--- Test 9: Clean detection after reset recovery ---");
        send_bit(1'b0, 1'b0);
        send_bit(1'b1, 1'b0);
        send_bit(1'b1, 1'b1); // Detected!

        // Final verification summary
        $display("========================================");
        $display("TEST RESULTS: %0d tests run, %0d errors", tests_run, errors);
        if (errors == 0) begin
            $display("TEST PASSED: Sequence detector verified successfully.");
        end else begin
            $display("TEST FAILED: Sequence detector encountered errors.");
        end
        $display("========================================");

        #20;
        if (errors == 0)
            $finish(0);
        else
            $finish(1);
    end

endmodule
