`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: top_monitored
// Description: Integrated Top-Level Wrapper module wrapping Phase 1 datapath
//              core with dual Ring Oscillator runtime hardware sensors.
//              - Sensor 1: Baseline Reference
//              - Sensor 2: Tapped onto high-risk rare trigger net (corner_case_flag)
// IEEE 1364-2001 Verilog Standard Compliant
//////////////////////////////////////////////////////////////////////////////////

module top_monitored (
    input  wire        clk,
    input  wire        rst,
    input  wire        enable,
    input  wire        test_mode,
    input  wire [31:0] data_in,
    input  wire [31:0] key_in,
    output wire [31:0] data_out,
    output wire        corner_case_flag,
    output wire [15:0] ro1_freq,
    output wire [15:0] ro2_freq,
    output wire [15:0] freq_delta
);

    // Datapath Top Module Instance
    top datapath_core (
        .clk(clk),
        .rst(rst),
        .enable(enable),
        .test_mode(test_mode),
        .data_in(data_in),
        .key_in(key_in),
        .data_out(data_out),
        .corner_case_flag(corner_case_flag)
    );

    // Sensor 1: Baseline Reference Sensor (Standard Datapath Environment)
    ring_oscillator ro_sensor1 (
        .enable(enable),
        .rare_net_in(1'b0),
        .ro_out(),
        .freq_count(ro1_freq)
    );

    // Sensor 2: Targeted Rare Net Sensor (Tapped on High-Risk Trigger Line corner_case_flag)
    ring_oscillator ro_sensor2 (
        .enable(enable),
        .rare_net_in(corner_case_flag),
        .ro_out(),
        .freq_count(ro2_freq)
    );

    // Frequency Delta (|RO1_freq - RO2_freq|)
    assign freq_delta = (ro1_freq >= ro2_freq) ? (ro1_freq - ro2_freq) : (ro2_freq - ro1_freq);

endmodule
