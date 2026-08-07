`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: tb_top
// Description: Phase 3 Testbench for Monitored Pipelined Datapath (top_monitored).
//              - Instantiates top_monitored module with dual RO sensors.
//              - Pass A: Standard Operation (test_mode = 0)
//              - Pass B: Target Corner-Case Mode (test_mode = 1)
//              - Logs sensor output traces to reports/runtime_sensor_data.csv
//              - Dumps VCD waveform trace
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
    wire [15:0] ro1_freq;
    wire [15:0] ro2_freq;
    wire [15:0] freq_delta;

    integer i;
    integer f_csv;

    // Instantiate Monitored Unit Under Test (UUT)
    top_monitored uut (
        .clk(clk),
        .rst(rst),
        .enable(enable),
        .test_mode(test_mode),
        .data_in(data_in),
        .key_in(key_in),
        .data_out(data_out),
        .corner_case_flag(corner_case_flag),
        .ro1_freq(ro1_freq),
        .ro2_freq(ro2_freq),
        .freq_delta(freq_delta)
    );

    // 100 MHz Clock Generation (Period = 10ns)
    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    // VCD Dump Waveform Logging
    initial begin
        $dumpfile("sim_output.vcd");
        $dumpvars(0, tb_top);
    end

    // Test Sequence & CSV Reporting
    initial begin
        // Open CSV Report file and write header
        f_csv = $fopen("reports/runtime_sensor_data.csv", "w");
        if (f_csv) begin
            $fdisplay(f_csv, "timestamp, test_mode, ro1_freq, ro2_freq, freq_delta");
        end

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
        // Pass A: Standard Operation (test_mode = 0)
        // ---------------------------------------------------------------------
        $display("=== Phase 3: Starting Pass A (Standard Operation, test_mode = 0) ===");
        test_mode = 1'b0;
        key_in    = 32'h1234_5678;

        for (i = 0; i < 50; i = i + 1) begin
            data_in = $random;
            @(posedge clk);
            if (f_csv) begin
                $fdisplay(f_csv, "%0t, %0d, %0d, %0d, %0d", $time, test_mode, ro1_freq, ro2_freq, freq_delta);
            end
            $display("[Pass A - Cycle %0d] data_in = 0x%8h | RO1 = %0d, RO2 = %0d, Delta = %0d",
                     i, data_in, ro1_freq, ro2_freq, freq_delta);
        end

        // Drain pipeline stages
        repeat (4) @(posedge clk);

        // ---------------------------------------------------------------------
        // Pass B: Target Corner-Case / Test Mode (test_mode = 1)
        // ---------------------------------------------------------------------
        $display("=== Phase 3: Starting Pass B (Corner-Case Mode, test_mode = 1) ===");
        test_mode = 1'b1;
        data_in   = 32'hA5A5_5A5A;
        key_in    = 32'h8765_4321;

        @(posedge clk);
        if (f_csv) begin
            $fdisplay(f_csv, "%0t, %0d, %0d, %0d, %0d", $time, test_mode, ro1_freq, ro2_freq, freq_delta);
        end
        $display("[Pass B - Trigger Vector] data_in = 0x%8h | RO1 = %0d, RO2 = %0d, Delta = %0d",
                 data_in, ro1_freq, ro2_freq, freq_delta);

        // Trace pipeline propagation and log frequency drops
        repeat (10) begin
            @(posedge clk);
            if (f_csv) begin
                $fdisplay(f_csv, "%0t, %0d, %0d, %0d, %0d", $time, test_mode, ro1_freq, ro2_freq, freq_delta);
            end
            $display("[Pass B - Trace] Flag = %b | RO1 = %0d, RO2 = %0d, Delta = %0d",
                     corner_case_flag, ro1_freq, ro2_freq, freq_delta);
        end

        if (f_csv) begin
            $fclose(f_csv);
        end

        #50;
        $display("=== Phase 3 Simulation Complete. CSV Logged to reports/runtime_sensor_data.csv ===");
        $finish;
    end

endmodule
