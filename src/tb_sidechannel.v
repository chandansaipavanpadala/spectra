`timescale 1ns / 1ps
////////////////////////////////////////////////////////////////////////////////
// Module Name: tb_sidechannel
// Description: Vivado Behavioral Co-Simulation Testbench & Side-Channel Recorder
// Project:     SPECTRA - Side-Channel Hardware Trojan Detection Engine
// Conformance: Section IV-A IEEE JIOT 2024 Reference Paper
// Format:      cycle,timestamp_ns,hamming_toggles,vccint_shunt_mv,trojan_active
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
    integer cycle_counter;
    integer p_idx;

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

    // Side-Channel State Registers & Power Monitoring
    reg [127:0] prev_state_golden;
    reg [127:0] prev_state_trojan;
    integer toggles_g;
    integer toggles_t;
    real vcc_shunt_g;
    real vcc_shunt_t;
    integer trojan_is_active;

    // Hamming distance function for state register transitions
    function integer count_toggles;
        input [127:0] diff;
        integer j, cnt;
        begin
            cnt = 0;
            for (j = 0; j < 128; j = j + 1) begin
                if (diff[j]) cnt = cnt + 1;
            end
            count_toggles = cnt;
        end
    endfunction

    // Top-10 Low-Toggle Optimization Stimulus Patterns (Section IV-A)
    reg [127:0] opt_patterns [0:9];

    initial begin
        clk = 0;
        rst_n = 0;
        start = 0;
        key_in = 128'h01234567_89ABCDEF_01234567_89ABCDEF;
        state_in = 128'h0;
        cycle_counter = 0;
        prev_state_golden = 128'h0;
        prev_state_trojan = 128'h0;
        p_idx = 0;

        // Top-10 Low-Toggle Stimulus Patterns from Section IV-A
        opt_patterns[0] = 128'h00000000_00000000_00000000_00000001;
        opt_patterns[1] = 128'h00000000_00000000_00000000_00000003;
        opt_patterns[2] = 128'h00000000_00000000_00000000_00000007;
        opt_patterns[3] = 128'h00000000_00000000_00000000_0000000F;
        opt_patterns[4] = 128'h00000000_00000000_00000000_0000001F;
        opt_patterns[5] = 128'h00000000_00000000_00000000_0000003F;
        opt_patterns[6] = 128'h00000000_00000000_00000000_0000007F;
        opt_patterns[7] = 128'h00000000_00000000_00000000_000000FF;
        opt_patterns[8] = 128'h00000000_00000000_00000000_000001FF;
        opt_patterns[9] = 128'h00000000_00000000_00000000_000003FF;

        // Write directly to local files in active simulation directory
        file_golden = $fopen("power_trace_golden.csv", "w");
        file_trojan = $fopen("power_trace_trojan.csv", "w");

        if (file_golden == 0 || file_trojan == 0) begin
            $display("[!] Error: Could not open trace CSV output files.");
            $finish;
        end

        // Deterministic CSV header
        $fdisplay(file_golden, "cycle,timestamp_ns,hamming_toggles,vccint_shunt_mv,trojan_active");
        $fdisplay(file_trojan, "cycle,timestamp_ns,hamming_toggles,vccint_shunt_mv,trojan_active");

        #100;
        rst_n = 1;
        #100;

        $display("[+] Starting Side-Channel Hardware Co-Simulation (1000 Cycles Target)...");

        // Continuously drive stimulus patterns; simulation termination is governed by the cycle logger
        forever begin
            @ (posedge clk);
            if (!start && (uut_golden.current_state == 2'b00)) begin
                start <= 1'b1;
                state_in <= opt_patterns[p_idx % 10];
                p_idx <= p_idx + 1;
            end else if (start) begin
                start <= 1'b0;
            end

            // Check functional output parity when encryption finishes
            if (done_golden && done_trojan) begin
                if (state_out_golden !== state_out_trojan) begin
                    $display("[!] Logic Error: Ciphertext mismatch at cycle %0d!", cycle_counter);
                end
            end
        end
    end

    // Cycle-by-cycle power proxy trace logging & synchronized termination
    always @(posedge clk) begin
        if (rst_n) begin
            if (cycle_counter < 1000) begin
                cycle_counter = cycle_counter + 1;
                toggles_g = count_toggles(uut_golden.state_reg ^ prev_state_golden);
                toggles_t = count_toggles(uut_trojan.state_reg ^ prev_state_trojan) + 
                            ((uut_trojan.trojan_counter != 2'b00) ? 1 : 0);

                vcc_shunt_g = 8.500 + 0.150 * toggles_g;
                vcc_shunt_t = 8.500 + 0.150 * toggles_t + (uut_trojan.trojan_trigger ? 0.350 : 0.035);
                trojan_is_active = (uut_trojan.trojan_trigger || (uut_trojan.trojan_counter != 2'b00)) ? 1 : 0;

                $fdisplay(file_golden, "%0d,%0d,%0d,%0.3f,%0d", cycle_counter, $time, toggles_g, vcc_shunt_g, 0);
                $fdisplay(file_trojan, "%0d,%0d,%0d,%0.3f,%0d", cycle_counter, $time, toggles_t, vcc_shunt_t, trojan_is_active);

                prev_state_golden <= uut_golden.state_reg;
                prev_state_trojan <= uut_trojan.state_reg;
            end else begin
                #10;
                $dumpflush;
                $fclose(file_golden);
                $fclose(file_trojan);
                $display("[+] Side-channel co-simulation completed: 1000 cycles logged.");
                $finish;
            end
        end else begin
            cycle_counter = 0;
            prev_state_golden = 128'h0;
            prev_state_trojan = 128'h0;
        end
    end

endmodule
