`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: ring_oscillator
// Description: Targeted 5-Stage Ring Oscillator Sensor Module.
//              - Measures local propagation delay shifts (delta_delay).
//              - Uses Xilinx Synthesis Keep/Dont_Touch attributes to preserve
//                combinational feedback loop structure.
// IEEE 1364-2001 Verilog Standard Compliant
//////////////////////////////////////////////////////////////////////////////////

module ring_oscillator (
    input  wire        enable,
    input  wire        rare_net_in,
    output wire        ro_out,
    output reg  [15:0] freq_count
);

    // Synthesis attributes to prevent Vivado EDA optimizer from trimming feedback loop
    (* KEEP = "TRUE", DONT_TOUCH = "TRUE" *) wire [5:0] node;

    // 5-Stage Combinational Loop: NAND gate control + 4 inverter stages
    // Tapping rare_net_in to introduce path delay shift on activation
    assign (* KEEP = "TRUE", DONT_TOUCH = "TRUE" *) node[0] = ~(enable & node[5]);
    assign (* KEEP = "TRUE", DONT_TOUCH = "TRUE" *) node[1] = ~node[0];
    assign (* KEEP = "TRUE", DONT_TOUCH = "TRUE" *) node[2] = ~node[1] ^ rare_net_in;
    assign (* KEEP = "TRUE", DONT_TOUCH = "TRUE" *) node[3] = ~node[2];
    assign (* KEEP = "TRUE", DONT_TOUCH = "TRUE" *) node[4] = ~node[3];
    assign (* KEEP = "TRUE", DONT_TOUCH = "TRUE" *) node[5] = ~node[4];

    assign ro_out = node[5];

    // 16-bit Frequency Counter incremented on every rising edge of ro_out
    always @(posedge ro_out or negedge enable) begin
        if (!enable) begin
            freq_count <= 16'h0000;
        end else begin
            freq_count <= freq_count + 1'b1;
        end
    end

endmodule
