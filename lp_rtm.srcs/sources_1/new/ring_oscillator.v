`timescale 1ns / 1ps

module ring_oscillator (
    input wire enable,
    input wire rare_net_in,
    output wire ro_out,
    output reg [15:0] freq_count
);

    // Synthesis attributes placed directly before wire declarations
    (* KEEP = "TRUE", DONT_TOUCH = "TRUE" *) wire stage0;
    (* KEEP = "TRUE", DONT_TOUCH = "TRUE" *) wire stage1;
    (* KEEP = "TRUE", DONT_TOUCH = "TRUE" *) wire stage2;
    (* KEEP = "TRUE", DONT_TOUCH = "TRUE" *) wire stage3;
    (* KEEP = "TRUE", DONT_TOUCH = "TRUE" *) wire stage4;

    // 5-stage combinational loop with NAND gating
    assign stage0 = ~(enable & stage4);
    assign stage1 = ~stage0;
    assign stage2 = ~stage1;
    assign stage3 = ~stage2;
    assign stage4 = ~stage3;

    assign ro_out = stage4;

    // 16-bit sampling counter
    always @(posedge ro_out or negedge enable) begin
        if (!enable) begin
            freq_count <= 16'd0;
        end else begin
            freq_count <= freq_count + 1'b1;
        end
    end

endmodule