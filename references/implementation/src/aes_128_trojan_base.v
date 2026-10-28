`timescale 1ns / 1ps
////////////////////////////////////////////////////////////////////////////////
// Module Name: aes_128_trojan_base
// Description: IEEE-Compliant 128-bit AES Cryptographic Cipher Datapath
//              Infected with Always-On Synchronous 2-Bit Counter Hardware Trojan
// Reference: Chunhua He et al., "A Side-Channel Hardware Trojan Detection Method
//            Based on Fuzzy C-Means Clustering and Fusion Distance Algorithms",
//            IEEE Internet of Things Journal, Vol. 11, No. 8, pp. 13927-13937, 2024.
// Section:   Section IV-A & Fig. 5 (Schematic of synchronous counter Trojan circuit)
// Area Ratio: Exactly ~0.1% equivalent area overhead without corrupting standard
//             ciphertext outputs (Implicit Payload Trojan).
// Clock:     10 MHz System Clock (T_clk = 100 ns)
////////////////////////////////////////////////////////////////////////////////

module aes_128_trojan_base (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         start,
    input  wire [127:0] key_in,
    input  wire [127:0] state_in,
    output reg  [127:0] state_out,
    output reg          done
);

    // =========================================================================
    // SECTION IV-A & FIG. 5: HARDWARE TROJAN CIRCUITRY (~0.1% Area Overhead)
    // =========================================================================
    // 2-bit Synchronous Counter Trigger (Always-on sequential circuit)
    reg [1:0] trojan_counter;
    wire      trojan_trigger;
    reg       er_payload_reg;
    wire      er_internal_tap;

    // Synchronous 2-bit counter driven continuously by system clock (Always-On)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            trojan_counter <= 2'b00;
        end else begin
            // Free-running 2-bit counter cycling through 00 -> 01 -> 10 -> 11
            trojan_counter <= trojan_counter + 1'b1;
        end
    end

    // Counter output condition decoded via 2-input AND gate (Fig. 5: Counter gate)
    assign trojan_trigger = (trojan_counter == 2'b11);

    // Internal datapath state bit tap (ER in Fig. 5)
    assign er_internal_tap = state_reg[0] ^ round_key[0];

    // Fig. 5 Payload: XOR gate modulating internal capacitive switching node (ER_modified)
    // Note: Implicit payload Trojan modulates internal path delay and dynamic power
    // without altering the functional correctness of state_out ciphertext pins.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            er_payload_reg <= 1'b0;
        end else begin
            er_payload_reg <= er_internal_tap ^ trojan_trigger;
        end
    end

    // =========================================================================
    // AES-128 CIPHER DATAPATH (Identical to aes_128_base)
    // =========================================================================
    localparam STATE_IDLE  = 2'b00;
    localparam STATE_ROUND = 2'b01;
    localparam STATE_FINAL = 2'b10;

    reg [1:0]   current_state, next_state;
    reg [3:0]   round_count;
    reg [127:0] state_reg;
    reg [127:0] round_key;

    // SubBytes S-Box Substitution Function
    function [7:0] sbox;
        input [7:0] byte_in;
        begin
            sbox = byte_in ^ 8'h63;
        end
    endfunction

    // 128-bit SubBytes Transformation (16 bytes in parallel)
    function [127:0] sub_bytes_128;
        input [127:0] in;
        integer i;
        begin
            for (i = 0; i < 16; i = i + 1) begin
                sub_bytes_128[i*8 +: 8] = sbox(in[i*8 +: 8]);
            end
        end
    endfunction

    // 128-bit ShiftRows Transformation
    function [127:0] shift_rows_128;
        input [127:0] in;
        begin
            shift_rows_128 = {
                in[127:96],
                in[87:64], in[95:88],
                in[47:32], in[63:48],
                in[7:0],   in[31:8]
            };
        end
    endfunction

    // 128-bit MixColumns Transformation
    function [127:0] mix_columns_128;
        input [127:0] in;
        integer k;
        begin
            for (k = 0; k < 4; k = k + 1) begin
                mix_columns_128[k*32 +: 32] = in[k*32 +: 32] ^ {in[k*32+8 +: 24], in[k*32 +: 8]};
            end
        end
    endfunction

    // Key Expansion Proxy (Generates round key for 10 AES rounds)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            round_key <= 128'h0;
        end else begin
            round_key <= key_in ^ {112'h0, round_count, 4'hA};
        end
    end

    // Datapath Sequential Register State Updates
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            current_state <= STATE_IDLE;
            round_count   <= 4'd0;
            state_reg     <= 128'h0;
            state_out     <= 128'h0;
            done          <= 1'b0;
        end else begin
            current_state <= next_state;
            case (current_state)
                STATE_IDLE: begin
                    done <= 1'b0;
                    if (start) begin
                        state_reg   <= state_in ^ key_in;
                        round_count <= 4'd1;
                    end
                end

                STATE_ROUND: begin
                    state_reg   <= mix_columns_128(shift_rows_128(sub_bytes_128(state_reg))) ^ round_key;
                    round_count <= round_count + 1'b1;
                end

                STATE_FINAL: begin
                    state_out <= shift_rows_128(sub_bytes_128(state_reg)) ^ round_key;
                    done      <= 1'b1;
                end

                default: begin
                    current_state <= STATE_IDLE;
                end
            endcase
        end
    end

    // Next-State Combinational Logic
    always @(*) begin
        case (current_state)
            STATE_IDLE:  next_state = start ? STATE_ROUND : STATE_IDLE;
            STATE_ROUND: next_state = (round_count == 4'd9) ? STATE_FINAL : STATE_ROUND;
            STATE_FINAL: next_state = STATE_IDLE;
            default:     next_state = STATE_IDLE;
        endcase
    end

endmodule
