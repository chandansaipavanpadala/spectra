`timescale 1ns / 1ps
////////////////////////////////////////////////////////////////////////////////
// Module Name: tb_sidechannel_base
// Description: Strict IEEE JIOT 2024 Base Paper Side-Channel Testbench
//              Applies Top-10 Low-Toggle Optimization Stimulus Vectors (Section IV-A)
//              and records cycle-by-cycle hardware switching traces.
// Reference:   Chunhua He et al., IEEE JIOT, Vol. 11, No. 8, pp. 13927-13937, 2024.
// Format:      cycle,timestamp_ns,hamming_toggles,vccint_shunt_mv,trojan_active
////////////////////////////////////////////////////////////////////////////////

module tb_sidechannel_base;

    // Testbench Signals
    reg         clk;
    reg         rst_n;
    reg         start;
    reg [127:0] key_in;
    reg [127:0] state_in;

    // Golden Core Interface
    wire [127:0] state_out_golden;
    wire         done_golden;

    // Trojan Core Interface
    wire [127:0] state_out_trojan;
    wire         done_trojan;

    // File Descriptors for Side-Channel Traces
    integer file_golden;
    integer file_trojan;
    integer cycle_counter;
    integer p_idx;

    // Instantiate Golden AES Core (aes_128_base)
    aes_128_base uut_golden (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .key_in(key_in),
        .state_in(state_in),
        .state_out(state_out_golden),
        .done(done_golden)
    );

    // Instantiate Trojan-Infected Core (aes_128_trojan_base)
    aes_128_trojan_base uut_trojan (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .key_in(key_in),
        .state_in(state_in),
        .state_out(state_out_trojan),
        .done(done_trojan)
    );

    // Clock Generation: 10 MHz (Period = 100 ns, Half-period = 50 ns)
    always #50 clk = ~clk;

    // Top-10 Low-Toggle Optimization Vectors (Section IV-A)
    reg [127:0] opt_patterns [0:9];

    // Power proxy calculation variables
    reg [127:0] prev_reg_g;
    reg [127:0] prev_reg_t;
    integer toggles_g;
    integer toggles_t;
    real vcc_g;
    real vcc_t;
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

    initial begin
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

        // Initialize signals
        clk = 0;
        rst_n = 0;
        start = 0;
        key_in = 128'h00010203_04050607_08090A0B_0C0D0E0F;
        state_in = 128'h0;
        cycle_counter = 0;
        prev_reg_g = 128'h0;
        prev_reg_t = 128'h0;
        p_idx = 0;

        // Write directly to local files in active simulation directory
        file_golden = $fopen("power_trace_golden.csv", "w");
        file_trojan = $fopen("power_trace_trojan.csv", "w");

        if (file_golden == 0 || file_trojan == 0) begin
            $display("[!] Error: Unable to open trace CSV files for writing.");
            $finish;
        end

        // Exact CSV header requested
        $fdisplay(file_golden, "cycle,timestamp_ns,hamming_toggles,vccint_shunt_mv,trojan_active");
        $fdisplay(file_trojan, "cycle,timestamp_ns,hamming_toggles,vccint_shunt_mv,trojan_active");

        #100;
        rst_n = 1;
        #100;

        $display("[+] Starting Base Paper Low-Toggle Side-Channel Acquisition (1000 Cycles)...");

        // Loop over the top-10 optimization patterns for 1000 clock cycles
        while (cycle_counter < 1000) begin
            @ (posedge clk);
            if (!start && (uut_golden.current_state == 2'b00)) begin
                start <= 1'b1;
                state_in <= opt_patterns[p_idx % 10];
                p_idx <= p_idx + 1;
            end else if (start) begin
                start <= 1'b0;
            end

            // Verify logic equivalence (Section II-B: functional testing)
            if (done_golden && done_trojan) begin
                if (state_out_golden !== state_out_trojan) begin
                    $display("[!] Logic Error: Output discrepancy detected at cycle %0d!", cycle_counter);
                end
            end
        end

        #100;
        $dumpflush;
        $fclose(file_golden);
        $fclose(file_trojan);
        $display("[+] tb_sidechannel_base simulation finished successfully: 1000 cycles logged.");
        $finish;
    end

    // Cycle-by-cycle power proxy trace logging
    always @(posedge clk) begin
        if (rst_n && (cycle_counter < 1000)) begin
            cycle_counter = cycle_counter + 1;
            toggles_g = count_toggles(uut_golden.state_reg ^ prev_reg_g);
            // In aes_128_trojan_base, always-on 2-bit counter toggles continuously (+1 or +2)
            toggles_t = count_toggles(uut_trojan.state_reg ^ prev_reg_t) + 
                        (uut_trojan.trojan_trigger ? 2 : 1);

            // Voltage proxy across shunt resistor (He et al. Fig. 6: ~8.5 mV base + toggles)
            vcc_g = 8.500 + 0.150 * toggles_g;
            vcc_t = 8.500 + 0.150 * toggles_t + (uut_trojan.trojan_trigger ? 0.350 : 0.035);
            trojan_is_active = (uut_trojan.trojan_counter != 2'b00 || uut_trojan.trojan_trigger) ? 1 : 0;

            $fdisplay(file_golden, "%0d,%0d,%0d,%0.3f,%0d", cycle_counter, $time, toggles_g, vcc_g, 0);
            $fdisplay(file_trojan, "%0d,%0d,%0d,%0.3f,%0d", cycle_counter, $time, toggles_t, vcc_t, trojan_is_active);

            prev_reg_g <= uut_golden.state_reg;
            prev_reg_t <= uut_trojan.state_reg;
        end
    end

endmodule
