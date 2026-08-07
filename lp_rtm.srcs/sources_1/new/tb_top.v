`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: tb_top
// Description: Testbench for 32-bit Pipelined Datapath Top Module.
//              - 100 MHz clock generation (10ns period)
//              - Pass 1: 50 random 32-bit inputs with test_mode = 0
//              - Pass 2: Target test vector 32'hA5A5_5A5A with test_mode = 1
//              - VCD trace logging
// IEEE 1364-2001 Verilog Standard Compliant
//////////////////////////////////////////////////////////////////////////////////

module tb_top;

    // Testbench Signals
    reg        clk;
    reg        rst;
    reg        enable;
    reg        test_mode;
    reg [31:0] data_in;
    reg [31:0] key_in;

    wire [31:0] data_out;
    wire        corner_case_flag;

    integer i;

    // Instantiate Unit Under Test (UUT)
    top uut (
        .clk(clk),
        .rst(rst),
        .enable(enable),
        .test_mode(test_mode),
        .data_in(data_in),
        .key_in(key_in),
        .data_out(data_out),
        .corner_case_flag(corner_case_flag)
    );

    // 100 MHz Clock Generation (Period = 10ns)
    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    // VCD Dump Logging
    initial begin
        $dumpfile("sim_output.vcd");
        $dumpvars(0, tb_top);
    end

    // Test Sequence
    initial begin
        // Initialize Inputs
        rst       = 1'b1;
        enable    = 1'b0;
        test_mode = 1'b0;
        data_in   = 32'h0;
        key_in    = 32'h0;

        // Apply Reset Sequence
        #20;
        rst = 1'b0;
        enable = 1'b1;
        #10;

        // ---------------------------------------------------------------------
        // Pass 1: Drive 50 random 32-bit inputs with test_mode = 0
        // ---------------------------------------------------------------------
        $display("=== Starting Pass 1: Normal Operation (test_mode = 0) ===");
        test_mode = 1'b0;
        key_in    = 32'h1234_5678;

        for (i = 0; i < 50; i = i + 1) begin
            data_in = $random;
            @(posedge clk);
            $display("[Pass 1 - Cycle %0d] data_in = 0x%8h | data_out = 0x%8h | corner_case_flag = %b",
                     i, data_in, data_out, corner_case_flag);
        end

        // Drain pipeline stages
        repeat (4) @(posedge clk);

        // ---------------------------------------------------------------------
        // Pass 2: Drive target test vector 32'hA5A5_5A5A with test_mode = 1
        // ---------------------------------------------------------------------
        $display("=== Starting Pass 2: DFT / Test Mode (test_mode = 1) ===");
        test_mode = 1'b1;
        data_in   = 32'hA5A5_5A5A;
        key_in    = 32'h8765_4321;

        @(posedge clk);
        $display("[Pass 2 - Vector Applied] data_in = 0x%8h (test_mode = %b)", data_in, test_mode);

        // Advance clock to trace pipeline propagation (4 pipeline stages)
        repeat (4) begin
            @(posedge clk);
            $display("[Pass 2 - Pipeline Trace] data_out = 0x%8h | corner_case_flag = %b",
                     data_out, corner_case_flag);
        end

        #50;
        $display("=== Simulation Complete ===");
        $finish;
    end

endmodule
