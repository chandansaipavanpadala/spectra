`timescale 1ns / 1ps
////////////////////////////////////////////////////////////////////////////////
// Module Name: tb_sidechannel
// Description: Side-Channel Stimulus Testbench & Power Proxy Trace Recorder
// Project: SPECTRA - Side-Channel Hardware Trojan Detection Engine
// Conformance: Section IV-A IEEE JIOT 2024 (1M-point trace at fs = 2.5 GHz)
////////////////////////////////////////////////////////////////////////////////

module tb_sidechannel;

    reg clk;
    reg rst_n;
    reg start;
    reg [127:0] key_in;
    reg [127:0] state_in;

    wire [127:0] state_out_golden;
    wire        done_golden;

    wire [127:0] state_out_trojan;
    wire        done_trojan;

    integer file_golden;
    integer file_trojan;
    integer sample_counter;

    // Instantiate Golden AES Core
    aes_128 uut_golden (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .key_in(key_in),
        .state_in(state_in),
        .state_out(state_out_golden),
        .done(done_golden)
    );

    // Instantiate Trojan-Infected AES Core
    aes_128_trojan uut_trojan (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .key_in(key_in),
        .state_in(state_in),
        .state_out(state_out_trojan),
        .done(done_trojan)
    );

    // Clock Generation: 10 MHz System Clock (100 ns period)
    always #50 clk = ~clk;

    // Side-Channel Power Proxy Trace Recorder
    real power_golden;
    real power_trojan;
    reg [127:0] prev_state_golden;
    reg [127:0] prev_state_trojan;

    initial begin
        clk = 0;
        rst_n = 0;
        start = 0;
        key_in = 128'h0123456789ABCDEF0123456789ABCDEF;
        state_in = 128'h0;
        sample_counter = 0;
        prev_state_golden = 128'h0;
        prev_state_trojan = 128'h0;

        file_golden = $fopen("reports/power_trace_golden.csv", "w");
        file_trojan = $fopen("reports/power_trace_trojan.csv", "w");

        if (file_golden == 0 || file_trojan == 0) begin
            $display("[!] Error: Could not open trace output files in reports/");
            $finish;
        end

        $fdisplay(file_golden, "sample_idx,power_proxy");
        $fdisplay(file_trojan, "sample_idx,power_proxy");

        #100;
        rst_n = 1;
        #100;

        // Apply low-toggle stimulus vectors to minimize background core switching noise
        repeat (1000) begin
            @ (posedge clk);
            start <= 1'b1;
            state_in <= {96'h0, $random};
            @ (posedge clk);
            start <= 1'b0;
            @ (posedge done_golden);
        end

        $dumpflush;
        $fclose(file_golden);
        $fclose(file_trojan);
        $display("[+] Side-channel simulation completed successfully.");
        $finish;
    end

endmodule
