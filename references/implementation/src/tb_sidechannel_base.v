`timescale 1ns / 1ps
////////////////////////////////////////////////////////////////////////////////
// Module Name: tb_sidechannel_base
// Description: Unified Side-Channel Co-Simulation Testbench (Base Paper)
//              Applies Top-10 Low-Toggle Optimization Stimulus Vectors (Section IV-A)
//              and logs deterministic cycle-by-cycle switching traces.
// Reference:   Chunhua He et al., IEEE JIOT, Vol. 11, No. 8, pp. 13927-13937, 2024
// Format:      cycle,timestamp_ns,hamming_toggles,vccint_shunt_v,cipher_match
////////////////////////////////////////////////////////////////////////////////

module tb_sidechannel_base;

    reg         clk;
    reg         rst_n;
    reg         start;
    reg [127:0] key_in;
    reg [127:0] state_in;

    wire [127:0] state_out_golden;
    wire         done_golden;
    wire [127:0] state_out_trojan;
    wire         done_trojan;

    integer fd_g;
    integer fd_t;
    integer cycle_counter;
    integer p_idx;
    integer wait_cycles;

    // Tracking registers for genuine bitwise Hamming transitions
    reg [127:0] prev_state_g;
    reg [127:0] prev_key_g;
    reg [127:0] prev_state_t;
    reg [127:0] prev_key_t;
    reg [1:0]   prev_trojan_cnt;
    reg         prev_payload_reg;

    integer core_toggles_g;
    integer core_toggles_t;
    integer trojan_toggles;
    integer toggles_g;
    integer toggles_t;
    real    vcc_shunt_g;
    real    vcc_shunt_t;
    integer cipher_match;

    // Golden AES Core
    aes_128_base uut_golden (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .key_in(key_in),
        .state_in(state_in),
        .state_out(state_out_golden),
        .done(done_golden)
    );

    // Trojan-Infected AES Core
    aes_128_trojan_base uut_trojan (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .key_in(key_in),
        .state_in(state_in),
        .state_out(state_out_trojan),
        .done(done_trojan)
    );

    // 10 MHz System Clock (100 ns period)
    always #50 clk = ~clk;

    // Global Watchdog Timer (5 ms timeout prevents Vivado hang)
    initial begin
        #5000000;
        $display("[WATCHDOG] Simulation timeout reached. Flushing files and exiting.");
        if (fd_g) begin
            $fflush(fd_g);
            $fclose(fd_g);
        end
        if (fd_t) begin
            $fflush(fd_t);
            $fclose(fd_t);
        end
        $finish;
    end

    // Bitwise Hamming Distance (popcount) over 128 bits
    function integer popcount128;
        input [127:0] vec;
        integer i, cnt;
        begin
            cnt = 0;
            for (i = 0; i < 128; i = i + 1) begin
                if (vec[i] === 1'b1) cnt = cnt + 1;
            end
            popcount128 = cnt;
        end
    endfunction

    // Top-10 Low-Toggle Stimulus Patterns (Section IV-A)
    reg [127:0] opt_patterns [0:9];

    initial begin
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

        clk              = 1'b0;
        rst_n            = 1'b0;
        start            = 1'b0;
        key_in           = 128'h00010203_04050607_08090A0B_0C0D0E0F;
        state_in         = 128'h0;
        cycle_counter    = 0;
        p_idx            = 0;
        wait_cycles      = 0;
        prev_state_g     = 128'h0;
        prev_key_g       = 128'h0;
        prev_state_t     = 128'h0;
        prev_key_t       = 128'h0;
        prev_trojan_cnt  = 2'b00;
        prev_payload_reg = 1'b0;

        fd_g = $fopen("power_trace_golden.csv", "w");
        fd_t = $fopen("power_trace_trojan.csv", "w");

        if (fd_g == 0 || fd_t == 0) begin
            $display("[!] Error: Unable to open trace CSV output files.");
            $finish;
        end

        $fdisplay(fd_g, "cycle,timestamp_ns,hamming_toggles,vccint_shunt_v,cipher_match");
        $fdisplay(fd_t, "cycle,timestamp_ns,hamming_toggles,vccint_shunt_v,cipher_match");

        #100;
        rst_n = 1'b1;
        #100;

        $display("[+] Starting Base Paper Side-Channel Co-Simulation (1000 Cycles Target)...");

        while (cycle_counter < 1000) begin
            @(posedge clk);
            if (uut_golden.current_state == 2'b00 && !start) begin
                start <= 1'b1;
                state_in <= opt_patterns[p_idx % 10];
                p_idx <= p_idx + 1;
                @(posedge clk);
                start <= 1'b0;

                wait_cycles = 0;
                while (done_golden !== 1'b1 && wait_cycles < 25 && cycle_counter < 1000) begin
                    @(posedge clk);
                    wait_cycles = wait_cycles + 1;
                end
            end
        end
    end

    // Cycle-by-cycle Hamming transition logging and bounded termination
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cycle_counter    <= 0;
            prev_state_g     <= 128'h0;
            prev_key_g       <= 128'h0;
            prev_state_t     <= 128'h0;
            prev_key_t       <= 128'h0;
            prev_trojan_cnt  <= 2'b00;
            prev_payload_reg <= 1'b0;
        end else begin
            if (cycle_counter < 1000) begin
                cycle_counter = cycle_counter + 1;

                core_toggles_g = popcount128(uut_golden.state_reg ^ prev_state_g) +
                                 popcount128(uut_golden.round_key ^ prev_key_g);

                core_toggles_t = popcount128(uut_trojan.state_reg ^ prev_state_t) +
                                 popcount128(uut_trojan.round_key ^ prev_key_t);

                trojan_toggles = ((uut_trojan.trojan_counter[0] !== prev_trojan_cnt[0]) ? 1 : 0) +
                                 ((uut_trojan.trojan_counter[1] !== prev_trojan_cnt[1]) ? 1 : 0) +
                                 ((uut_trojan.er_payload_reg    !== prev_payload_reg)   ? 1 : 0);

                toggles_g = core_toggles_g;
                toggles_t = core_toggles_t + trojan_toggles;

                // Shunt resistor (0.5 Ohm) voltage proxy in Volts driven strictly by RTL toggles
                vcc_shunt_g = 0.008500 + 0.000150 * core_toggles_g;
                vcc_shunt_t = 0.008500 + 0.000150 * core_toggles_t + 0.000045 * trojan_toggles;

                // Verify Golden vs. Trojan functional equivalence on every cycle
                cipher_match = (state_out_golden === state_out_trojan) ? 1 : 0;
                if (cipher_match == 0) begin
                    $display("[!] Logic Error: Ciphertext mismatch at cycle %0d!", cycle_counter);
                end

                $fdisplay(fd_g, "%0d,%0d,%0d,%0.6f,%0d", cycle_counter, $time, toggles_g, vcc_shunt_g, cipher_match);
                $fdisplay(fd_t, "%0d,%0d,%0d,%0.6f,%0d", cycle_counter, $time, toggles_t, vcc_shunt_t, cipher_match);

                prev_state_g     <= uut_golden.state_reg;
                prev_key_g       <= uut_golden.round_key;
                prev_state_t     <= uut_trojan.state_reg;
                prev_key_t       <= uut_trojan.round_key;
                prev_trojan_cnt  <= uut_trojan.trojan_counter;
                prev_payload_reg <= uut_trojan.er_payload_reg;
            end else begin
                if (fd_g) begin
                    $fflush(fd_g);
                    $fclose(fd_g);
                end
                if (fd_t) begin
                    $fflush(fd_t);
                    $fclose(fd_t);
                end
                $display("[+] tb_sidechannel_base simulation completed successfully: 1000 cycles logged.");
                $finish;
            end
        end
    end

endmodule
