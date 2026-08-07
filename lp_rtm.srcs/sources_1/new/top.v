`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: top
// Description: 32-bit Multi-Stage Pipelined Datapath with AES-like
//              Substitution/Permutation Round & DFT Conditional Path.
// IEEE 1364-2001 Verilog Standard Compliant
//////////////////////////////////////////////////////////////////////////////////

module top (
    input  wire        clk,
    input  wire        rst,
    input  wire        enable,
    input  wire        test_mode,
    input  wire [31:0] data_in,
    input  wire [31:0] key_in,
    output reg  [31:0] data_out,
    output reg         corner_case_flag
);

    // Target Test Pattern for DFT / Corner-Case Detection
    localparam [31:0] TEST_PATTERN = 32'hA5A5_5A5A;

    // Pipeline Stage 1 Registers
    reg [31:0] stage1_data;
    reg [31:0] stage1_key;
    reg        stage1_test_mode;
    reg        stage1_pattern_match;

    // Pipeline Stage 2 Registers
    reg [31:0] stage2_data;
    reg        stage2_test_mode;
    reg        stage2_pattern_match;

    // Pipeline Stage 3 Registers
    reg [31:0] stage3_data;
    reg        stage3_test_mode;
    reg        stage3_pattern_match;

    // Intermediate Transformation Signals
    wire [31:0] s1_sub_bytes;
    wire [31:0] s2_shift_rows;
    wire [31:0] s3_mix_columns;

    // =========================================================================
    // Stage 1: Key XOR & Byte-wise Nonlinear Substitution (SubBytes)
    // =========================================================================
    assign s1_sub_bytes[7:0]   = (data_in[7:0]   ^ key_in[7:0])   ^ 8'h63;
    assign s1_sub_bytes[15:8]  = (data_in[15:8]  ^ key_in[15:8])  ^ 8'h7C;
    assign s1_sub_bytes[23:16] = (data_in[23:16] ^ key_in[23:16]) ^ 8'h77;
    assign s1_sub_bytes[31:24] = (data_in[31:24] ^ key_in[31:24]) ^ 8'h7B;

    always @(posedge clk) begin
        if (rst) begin
            stage1_data          <= 32'h0;
            stage1_key           <= 32'h0;
            stage1_test_mode     <= 1'b0;
            stage1_pattern_match <= 1'b0;
        end else if (enable) begin
            stage1_data          <= s1_sub_bytes;
            stage1_key           <= key_in;
            stage1_test_mode     <= test_mode;
            stage1_pattern_match <= (data_in == TEST_PATTERN);
        end
    end

    // =========================================================================
    // Stage 2: Byte Permutation & Rotation (ShiftRows)
    // =========================================================================
    // Circular byte rotation: Byte 0 -> Byte 1 -> Byte 2 -> Byte 3
    assign s2_shift_rows = {stage1_data[23:16], stage1_data[15:8], stage1_data[7:0], stage1_data[31:24]};

    always @(posedge clk) begin
        if (rst) begin
            stage2_data          <= 32'h0;
            stage2_test_mode     <= 1'b0;
            stage2_pattern_match <= 1'b0;
        end else if (enable) begin
            stage2_data          <= s2_shift_rows;
            stage2_test_mode     <= stage1_test_mode;
            stage2_pattern_match <= stage1_pattern_match;
        end
    end

    // =========================================================================
    // Stage 3: Linear Bitwise Combination & Constant XOR (MixColumns)
    // =========================================================================
    assign s3_mix_columns[7:0]   = stage2_data[7:0]   ^ stage2_data[15:8]  ^ 8'h1F;
    assign s3_mix_columns[15:8]  = stage2_data[15:8]  ^ stage2_data[23:16] ^ 8'h3D;
    assign s3_mix_columns[23:16] = stage2_data[23:16] ^ stage2_data[31:24] ^ 8'h5A;
    assign s3_mix_columns[31:24] = stage2_data[31:24] ^ stage2_data[7:0]   ^ 8'h79;

    always @(posedge clk) begin
        if (rst) begin
            stage3_data          <= 32'h0;
            stage3_test_mode     <= 1'b0;
            stage3_pattern_match <= 1'b0;
        end else if (enable) begin
            stage3_data          <= s3_mix_columns;
            stage3_test_mode     <= stage2_test_mode;
            stage3_pattern_match <= stage2_pattern_match;
        end
    end

    // =========================================================================
    // Output Stage: DFT Conditional Path & Data Formatting
    // =========================================================================
    always @(posedge clk) begin
        if (rst) begin
            data_out         <= 32'h0;
            corner_case_flag <= 1'b0;
        end else if (enable) begin
            if (stage3_test_mode && stage3_pattern_match) begin
                // DFT / Corner-case trigger active: Assert flag and invert bit 0 of output
                corner_case_flag <= 1'b1;
                data_out         <= {stage3_data[31:1], ~stage3_data[0]};
            end else begin
                // Normal datapath operation
                corner_case_flag <= 1'b0;
                data_out         <= stage3_data;
            end
        end
    end

endmodule
