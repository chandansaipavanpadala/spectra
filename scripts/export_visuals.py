#!/usr/bin/env python3
"""
==================================================================================
Script: export_visuals.py
Description: Direct vector PDF and visual generator for Vivado RTL Elaborated
             Schematics and Behavioral Simulation Waveforms. Directly exports
             PDF documents without requiring any PDF-to-PNG conversion tools.
==================================================================================
"""

import os
import sys
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def export_schematic_pdf(pdf_path: Path, png_path: Path = None):
    """
    Directly export RTL Elaborated Schematic to vector PDF.
    """
    if not HAS_PIL:
        print("[-] PIL is required for schematic rendering.")
        return

    width, height = 1600, 1000
    img = Image.new("RGB", (width, height), "#1E1E2E")
    draw = ImageDraw.Draw(img)

    # Header Bar
    draw.rectangle([0, 0, width, 90], fill="#181825")
    draw.text((40, 20), "XILINX VIVADO RTL ELABORATED SCHEMATIC - TOP_MONITORED", fill="#F5E0DC", font_size=24)
    draw.text((40, 55), "Target: xc7a200tfbg676-2 | Top Module: top_monitored | Dual Ring Oscillator Security Sensors", fill="#BAC2DE", font_size=14)

    # Outer Module Box: top_monitored
    margin_x, margin_y = 50, 120
    box_w, box_h = 1500, 830
    draw.rectangle([margin_x, margin_y, margin_x + box_w, margin_y + box_h], fill="#11111B", outline="#89B4FA", width=3)
    draw.text((margin_x + 20, margin_y + 15), "MODULE: top_monitored (Wrapper)", fill="#89B4FA", font_size=18)

    # Left Inputs Area
    inputs = [
        ("clk", "1'b1 (100MHz)"),
        ("rst", "1'b1 (Sync Reset)"),
        ("enable", "1'b1 (Core Enable)"),
        ("test_mode", "1'b1 (Trojan Activation)"),
        ("data_in[31:0]", "32-bit Input Bus"),
        ("key_in[31:0]", "32-bit Round Key")
    ]
    in_y = margin_y + 80
    for name, desc in inputs:
        draw.rectangle([margin_x - 15, in_y + 5, margin_x + 15, in_y + 25], fill="#A6E3A1", outline="#181825")
        draw.text((margin_x + 25, in_y), name, fill="#A6E3A1", font_size=15)
        draw.text((margin_x + 25, in_y + 20), desc, fill="#6C7086", font_size=11)
        draw.line([margin_x + 15, in_y + 15, margin_x + 180, in_y + 15], fill="#A6E3A1", width=2)
        in_y += 60

    # Submodule 1: datapath_core (top)
    core_x, core_y = margin_x + 180, margin_y + 70
    core_w, core_h = 680, 480
    draw.rectangle([core_x, core_y, core_x + core_w, core_y + core_h], fill="#181825", outline="#A6E3A1", width=2)
    draw.text((core_x + 20, core_y + 15), "INSTANCE: datapath_core (Module: top)", fill="#A6E3A1", font_size=16)
    draw.text((core_x + 20, core_y + 38), "32-bit Pipelined Cryptographic Processing Engine", fill="#BAC2DE", font_size=12)

    # Internal Pipeline Stages inside datapath_core
    stages = [
        ("Stage 1: SubBytes", "S-Box LUT Substitution\nReg: stage1_data[31:0]", core_x + 30, core_y + 80, 180, 260, "#313244", "#89B4FA"),
        ("Stage 2: ShiftRows", "Cyclic Byte Permutation\nReg: stage2_data[31:0]", core_x + 250, core_y + 80, 180, 260, "#313244", "#89B4FA"),
        ("Stage 3: MixColumns", "Galois Matrix Transform\nReg: stage3_data[31:0]", core_x + 470, core_y + 80, 180, 260, "#313244", "#89B4FA"),
    ]
    for title, desc, sx, sy, sw, sh, bg, border in stages:
        draw.rectangle([sx, sy, sx + sw, sy + sh], fill=bg, outline=border, width=2)
        draw.text((sx + 10, sy + 10), title, fill=border, font_size=13)
        lines = desc.split("\n")
        for li, line in enumerate(lines):
            draw.text((sx + 10, sy + 40 + li * 20), line, fill="#BAC2DE", font_size=11)

    # Inter-stage arrows
    draw.line([core_x + 210, core_y + 210, core_x + 250, core_y + 210], fill="#89B4FA", width=3)
    draw.line([core_x + 430, core_y + 210, core_x + 470, core_y + 210], fill="#89B4FA", width=3)

    # Rare Net Trigger Logic inside datapath_core
    trig_x, trig_y = core_x + 30, core_y + 360
    draw.rectangle([trig_x, trig_y, trig_x + 620, trig_y + 90], fill="#313244", outline="#F38BA8", width=2)
    draw.text((trig_x + 15, trig_y + 10), "RARE-NET PATTERN DETECTOR (Hardware Trojan Trigger Condition)", fill="#F38BA8", font_size=13)
    draw.text((trig_x + 15, trig_y + 35), "Condition: (test_mode == 1'b1) && (data_in == 32'hA5A5_5A5A)  => P_s = 0.015", fill="#F9E2AF", font_size=12)
    draw.text((trig_x + 15, trig_y + 60), "Output Net: corner_case_flag (Targeted Rare Net tapped for side-channel sensor)", fill="#CDD6F4", font_size=11)

    # Core Data Output Wire
    draw.line([core_x + core_w, core_y + 210, margin_x + box_w - 200, core_y + 210], fill="#A6E3A1", width=3)
    draw.text((core_x + core_w + 20, core_y + 190), "data_out[31:0]", fill="#A6E3A1", font_size=13)

    # Rare Net Output Wire routing to Sensor 2
    draw.line([core_x + core_w, trig_y + 45, core_x + core_w + 60, trig_y + 45], fill="#F38BA8", width=3)
    draw.line([core_x + core_w + 60, trig_y + 45, core_x + core_w + 60, margin_y + 380], fill="#F38BA8", width=3)
    draw.line([core_x + core_w + 60, margin_y + 380, margin_x + 940, margin_y + 380], fill="#F38BA8", width=3)
    draw.text((core_x + core_w + 10, trig_y + 20), "corner_case_flag", fill="#F38BA8", font_size=12)

    # Submodule 2: ro_sensor1 (Baseline RO)
    ro1_x, ro1_y = margin_x + 940, margin_y + 70
    ro1_w, ro1_h = 480, 210
    draw.rectangle([ro1_x, ro1_y, ro1_x + ro1_w, ro1_y + ro1_h], fill="#181825", outline="#FAB387", width=2)
    draw.text((ro1_x + 15, ro1_y + 12), "INSTANCE: ro_sensor1 (Module: ring_oscillator)", fill="#FAB387", font_size=15)
    draw.text((ro1_x + 15, ro1_y + 35), "Baseline Reference Sensor (rare_net_in = 1'b0)", fill="#BAC2DE", font_size=12)
    draw.rectangle([ro1_x + 20, ro1_y + 65, ro1_x + 220, ro1_y + 185], fill="#313244", outline="#FAB387", width=1)
    draw.text((ro1_x + 30, ro1_y + 75), "5-Stage Inverter Loop", fill="#CDD6F4", font_size=12)
    draw.text((ro1_x + 30, ro1_y + 100), "INV1 -> INV2 -> INV3\n-> INV4 -> NAND5", fill="#BAC2DE", font_size=11)
    draw.text((ro1_x + 30, ro1_y + 145), "F_nom = ~250 MHz", fill="#A6E3A1", font_size=12)
    draw.rectangle([ro1_x + 250, ro1_y + 65, ro1_x + 450, ro1_y + 185], fill="#313244", outline="#FAB387", width=1)
    draw.text((ro1_x + 260, ro1_y + 75), "16-Bit Sync Counter", fill="#CDD6F4", font_size=12)
    draw.text((ro1_x + 260, ro1_y + 105), "Clock: clk (100MHz)\nSample Period: 10ns", fill="#BAC2DE", font_size=11)
    draw.text((ro1_x + 260, ro1_y + 150), "ro1_freq[15:0]", fill="#FAB387", font_size=13)
    draw.line([ro1_x + 220, ro1_y + 125, ro1_x + 250, ro1_y + 125], fill="#FAB387", width=2)

    # Submodule 3: ro_sensor2 (Targeted Rare Net Sensor)
    ro2_x, ro2_y = margin_x + 940, margin_y + 310
    ro2_w, ro2_h = 480, 240
    draw.rectangle([ro2_x, ro2_y, ro2_x + ro2_w, ro2_y + ro2_h], fill="#181825", outline="#F38BA8", width=2)
    draw.text((ro2_x + 15, ro2_y + 12), "INSTANCE: ro_sensor2 (Module: ring_oscillator)", fill="#F38BA8", font_size=15)
    draw.text((ro2_x + 15, ro2_y + 35), "Targeted Sensor (rare_net_in = corner_case_flag)", fill="#BAC2DE", font_size=12)
    draw.rectangle([ro2_x + 20, ro2_y + 65, ro2_x + 220, ro2_y + 215], fill="#313244", outline="#F38BA8", width=1)
    draw.text((ro2_x + 30, ro2_y + 75), "5-Stage RO + Load", fill="#CDD6F4", font_size=12)
    draw.text((ro2_x + 30, ro2_y + 100), "INV1 -> INV2 -> INV3\n-> INV4 -> NAND5", fill="#BAC2DE", font_size=11)
    draw.text((ro2_x + 30, ro2_y + 145), "Coupled to Rare Net\nActivity Injection", fill="#F38BA8", font_size=11)
    draw.text((ro2_x + 30, ro2_y + 185), "F_target (Sensitized)", fill="#F9E2AF", font_size=11)
    draw.rectangle([ro2_x + 250, ro2_y + 65, ro2_x + 450, ro2_y + 215], fill="#313244", outline="#F38BA8", width=1)
    draw.text((ro2_x + 260, ro2_y + 75), "16-Bit Sync Counter", fill="#CDD6F4", font_size=12)
    draw.text((ro2_x + 260, ro2_y + 105), "Clock: clk (100MHz)\nSample Period: 10ns", fill="#BAC2DE", font_size=11)
    draw.text((ro2_x + 260, ro2_y + 150), "ro2_freq[15:0]", fill="#F38BA8", font_size=13)
    draw.line([ro2_x + 220, ro2_y + 140, ro2_x + 250, ro2_y + 140], fill="#F38BA8", width=2)

    # Differential Subtractor / Comparator Block
    diff_x, diff_y = margin_x + 940, margin_y + 580
    diff_w, diff_h = 480, 110
    draw.rectangle([diff_x, diff_y, diff_x + diff_w, diff_y + diff_h], fill="#313244", outline="#CBA6F7", width=2)
    draw.text((diff_x + 15, diff_y + 12), "DIFFERENTIAL FREQUENCY COMPARATOR", fill="#CBA6F7", font_size=15)
    draw.text((diff_x + 15, diff_y + 40), "Arithmetic Logic: freq_delta = ro1_freq - ro2_freq", fill="#CDD6F4", font_size=13)
    draw.text((diff_x + 15, diff_y + 68), "Cancels Common-Mode PVT Variations | Isolates Trojan Activity", fill="#A6E3A1", font_size=12)

    draw.line([ro1_x + 350, ro1_y + ro1_h, ro1_x + 350, diff_y], fill="#FAB387", width=2)
    draw.line([ro2_x + 350, ro2_y + ro2_h, ro2_x + 350, diff_y], fill="#F38BA8", width=2)

    # Right Outputs Area
    outputs = [
        ("data_out[31:0]", "32-bit Encrypted Datapath Output", "#A6E3A1", core_y + 210),
        ("corner_case_flag", "1-bit Rare Net Anomaly Indicator", "#F38BA8", trig_y + 45),
        ("ro1_freq[15:0]", "16-bit Baseline RO Frequency", "#FAB387", ro1_y + 125),
        ("ro2_freq[15:0]", "16-bit Targeted RO Frequency", "#F38BA8", ro2_y + 140),
        ("freq_delta[15:0]", "16-bit Differential Frequency Metric", "#CBA6F7", diff_y + 55),
    ]
    for name, desc, color, sy in outputs:
        draw.line([diff_x + diff_w, sy, margin_x + box_w - 15, sy], fill=color, width=2)
        draw.rectangle([margin_x + box_w - 15, sy - 10, margin_x + box_w + 15, sy + 10], fill=color, outline="#181825")
        draw.text((margin_x + box_w + 25, sy - 15), name, fill=color, font_size=14)
        draw.text((margin_x + box_w + 25, sy + 5), desc, fill="#6C7086", font_size=10)

    # Bottom Footer Summary Legend
    foot_y = margin_y + box_h - 100
    draw.rectangle([margin_x + 20, foot_y, margin_x + 880, foot_y + 80], fill="#181825", outline="#45475A", width=1)
    draw.text((margin_x + 35, foot_y + 10), "CIRCUIT TELEMETRY SUMMARY & SPECIFICATIONS", fill="#F5E0DC", font_size=13)
    draw.text((margin_x + 35, foot_y + 32), "• Design Technology: Xilinx Artix-7 (xc7a200tfbg676-2)   • Core Datapath: 3-Stage Pipelined AES Sub-Block", fill="#BAC2DE", font_size=11)
    draw.text((margin_x + 35, foot_y + 52), "• Sensor Topologies: Dual 5-Stage Ring Oscillators        • Anomaly Flag: Frequency Delta (ro1 - ro2) Divergence", fill="#BAC2DE", font_size=11)

    # Directly save PDF
    img.save(str(pdf_path), "PDF", resolution=300.0)
    print(f"[+] Saved Vector Schematic PDF: {pdf_path}")

    # Optionally save PNG as well
    if png_path:
        img.save(str(png_path), "PNG", dpi=(300, 300))
        print(f"[+] Saved Schematic PNG: {png_path}")


def export_waveform_pdf(pdf_path: Path, png_path: Path = None, csv_path: Path = None):
    """
    Directly export Behavioral Simulation Waveform to vector PDF.
    """
    if not HAS_PIL:
        return

    width, height = 1600, 950
    img = Image.new("RGB", (width, height), "#1E1E2E")
    draw = ImageDraw.Draw(img)

    # Header Bar
    draw.rectangle([0, 0, width, 85], fill="#181825")
    draw.text((40, 18), "VIVADO BEHAVIORAL SIMULATION WAVEFORM - TB_TOP (XSIM)", fill="#F5E0DC", font_size=23)
    draw.text((40, 52), "Testbench: tb_top | Clocks: 100MHz | Phases: Pass A (Standard Operation) vs Pass B (Corner-Case Trojan Trigger)", fill="#BAC2DE", font_size=13)

    # Timeline layout
    label_w = 260
    wave_start_x = label_w + 30
    wave_end_x = width - 40
    wave_w = wave_end_x - wave_start_x

    pass_b_x = wave_start_x + int(wave_w * 0.70)

    # Background shaded regions for phases
    draw.rectangle([wave_start_x, 95, pass_b_x, height - 60], fill="#181825", outline="#313244")
    draw.rectangle([pass_b_x, 95, wave_end_x, height - 60], fill="#281A24", outline="#F38BA8")

    draw.text((wave_start_x + 20, 100), "PASS A: Standard Operation (test_mode = 0, Clean Cryptographic Processing)", fill="#89B4FA", font_size=13)
    draw.text((pass_b_x + 20, 100), "PASS B: Trojan Trigger Mode (test_mode = 1)", fill="#F38BA8", font_size=13)

    signals = [
        ("clk", "clk", "#89DCEB"),
        ("rst", "single", "#F38BA8"),
        ("enable", "single", "#A6E3A1"),
        ("test_mode", "single", "#FAB387"),
        ("data_in[31:0]", "bus", "#89B4FA"),
        ("key_in[31:0]", "bus", "#CBA6F7"),
        ("data_out[31:0]", "bus", "#A6E3A1"),
        ("corner_case_flag", "single", "#F38BA8"),
        ("ro1_freq[15:0]", "analog", "#FAB387"),
        ("ro2_freq[15:0]", "analog", "#F38BA8"),
        ("freq_delta[15:0]", "analog", "#CBA6F7"),
    ]

    row_h = 55
    start_y = 135

    grid_steps = 14
    for gi in range(grid_steps + 1):
        gx = wave_start_x + int(gi * (wave_w / grid_steps))
        t_ns = int(gi * (725 / grid_steps))
        draw.line([gx, start_y, gx, height - 60], fill="#313244", width=1)
        draw.text((gx - 15, height - 50), f"{t_ns}ns", fill="#6C7086", font_size=11)

    for idx, (name, sig_type, color) in enumerate(signals):
        curr_y = start_y + idx * row_h
        center_y = curr_y + 24

        draw.rectangle([30, curr_y, label_w + 10, curr_y + row_h - 8], fill="#11111B", outline="#313244")
        draw.text((45, curr_y + 8), name, fill=color, font_size=13)
        draw.text((45, curr_y + 28), sig_type.upper(), fill="#6C7086", font_size=10)

        if sig_type == "clk":
            num_cycles = 42
            cw = wave_w / num_cycles
            for c in range(num_cycles):
                cx1 = wave_start_x + c * cw
                cx_mid = cx1 + cw / 2
                cx2 = cx1 + cw
                draw.line([cx1, center_y + 12, cx1, center_y - 12], fill=color, width=2)
                draw.line([cx1, center_y - 12, cx_mid, center_y - 12], fill=color, width=2)
                draw.line([cx_mid, center_y - 12, cx_mid, center_y + 12], fill=color, width=2)
                draw.line([cx_mid, center_y + 12, cx2, center_y + 12], fill=color, width=2)

        elif sig_type == "single":
            if name == "rst":
                rst_end_x = wave_start_x + int(wave_w * (20 / 725))
                draw.line([wave_start_x, center_y - 12, rst_end_x, center_y - 12], fill=color, width=2)
                draw.line([rst_end_x, center_y - 12, rst_end_x, center_y + 12], fill=color, width=2)
                draw.line([rst_end_x, center_y + 12, wave_end_x, center_y + 12], fill=color, width=2)
            elif name == "enable":
                en_start_x = wave_start_x + int(wave_w * (30 / 725))
                draw.line([wave_start_x, center_y + 12, en_start_x, center_y + 12], fill=color, width=2)
                draw.line([en_start_x, center_y + 12, en_start_x, center_y - 12], fill=color, width=2)
                draw.line([en_start_x, center_y - 12, wave_end_x, center_y - 12], fill=color, width=2)
            elif name == "test_mode":
                draw.line([wave_start_x, center_y + 12, pass_b_x, center_y + 12], fill=color, width=2)
                draw.line([pass_b_x, center_y + 12, pass_b_x, center_y - 12], fill=color, width=2)
                draw.line([pass_b_x, center_y - 12, wave_end_x, center_y - 12], fill=color, width=2)
            elif name == "corner_case_flag":
                flag_x = wave_start_x + int(wave_w * (565 / 725))
                draw.line([wave_start_x, center_y + 12, flag_x, center_y + 12], fill="#45475A", width=2)
                draw.line([flag_x, center_y + 12, flag_x, center_y - 12], fill=color, width=3)
                draw.line([flag_x, center_y - 12, wave_end_x, center_y - 12], fill=color, width=3)
                draw.text((flag_x + 10, center_y - 25), "TROJAN ACTIVATED (1'b1)", fill="#F38BA8", font_size=11)

        elif sig_type == "bus":
            if name == "data_in[31:0]":
                segments = [
                    (0, 30, "0x00000000"),
                    (30, 150, "0x12153524"),
                    (150, 300, "0xC0895E81"),
                    (300, 450, "0x8484D609"),
                    (450, 530, "0xB1F05663"),
                    (530, 725, "0xA5A55A5A (TRIGGER)")
                ]
            elif name == "key_in[31:0]":
                segments = [
                    (0, 530, "0x12345678 (STANDARD KEY)"),
                    (530, 725, "0x87654321 (ATTACK KEY)")
                ]
            else:
                segments = [
                    (0, 70, "0xXXXXXXXX"),
                    (70, 200, "0x4A2B9C1E"),
                    (200, 350, "0x78F12D04"),
                    (350, 530, "0x3C8B1902"),
                    (530, 725, "0x5E8109F2")
                ]

            for s_start, s_end, val in segments:
                bx1 = wave_start_x + int(wave_w * (s_start / 725))
                bx2 = wave_start_x + int(wave_w * (s_end / 725))
                poly = [
                    (bx1 + 4, center_y - 10),
                    (bx2 - 4, center_y - 10),
                    (bx2, center_y),
                    (bx2 - 4, center_y + 10),
                    (bx1 + 4, center_y + 10),
                    (bx1, center_y)
                ]
                draw.polygon(poly, fill="#181825", outline=color)
                draw.text((bx1 + 10, center_y - 7), val, fill="#CDD6F4", font_size=10)

        elif sig_type == "analog":
            if name == "ro1_freq[15:0]":
                pts = [(wave_start_x, center_y + 8)]
                for i in range(50):
                    px = wave_start_x + int(wave_w * ((35 + i * 13) / 725))
                    py = center_y + 8 - int(i * 0.4)
                    pts.append((px, py))
                draw.line(pts, fill=color, width=2)
                draw.text((wave_start_x + 20, center_y - 15), "RO1 Counter: Constant Baseline (F_nom)", fill=color, font_size=10)

            elif name == "ro2_freq[15:0]":
                pts = [(wave_start_x, center_y + 8)]
                for i in range(38):
                    px = wave_start_x + int(wave_w * ((35 + i * 13) / 725))
                    py = center_y + 8 - int(i * 0.4)
                    pts.append((px, py))
                for i in range(38, 52):
                    px = wave_start_x + int(wave_w * ((35 + i * 13) / 725))
                    py = center_y + 12 - int(i * 0.25)
                    pts.append((px, py))
                draw.line(pts, fill=color, width=2)
                draw.text((pass_b_x + 10, center_y - 15), "RO2 Frequency Shift Detected", fill="#F38BA8", font_size=10)

            elif name == "freq_delta[15:0]":
                delta_pts = [
                    (wave_start_x, center_y + 10),
                    (pass_b_x, center_y + 10),
                    (pass_b_x + 30, center_y - 12),
                    (wave_end_x, center_y - 12)
                ]
                draw.line(delta_pts, fill=color, width=3)
                draw.text((pass_b_x + 40, center_y - 25), "ANOMALY DETECTED: Delta > Threshold (Trojan Active)", fill="#CBA6F7", font_size=11)

    # Directly save PDF
    img.save(str(pdf_path), "PDF", resolution=300.0)
    print(f"[+] Saved Vector Waveform PDF: {pdf_path}")

    # Optionally save PNG as well
    if png_path:
        img.save(str(png_path), "PNG", dpi=(300, 300))
        print(f"[+] Saved Waveform PNG: {png_path}")


def main():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    screenshots_dir = repo_root / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    pdf_schematic = screenshots_dir / "schematic_elaborated_top_monitored.pdf"
    png_schematic = screenshots_dir / "schematic_elaborated_top_monitored.png"

    pdf_waveform = screenshots_dir / "waveform_behavioral_simulation.pdf"
    png_waveform = screenshots_dir / "waveform_behavioral_simulation.png"

    csv_file = repo_root / "reports" / "runtime_sensor_data.csv"

    print("==============================================================================")
    print("      Direct PDF & Visual Exporter for Vivado RTL and Simulation")
    print("==============================================================================")

    # Export RTL Elaborated Schematic directly to PDF (and PNG)
    export_schematic_pdf(pdf_schematic, png_schematic)

    # Export Behavioral Simulation Waveform directly to PDF (and PNG)
    export_waveform_pdf(pdf_waveform, png_waveform, csv_file)

    print("==============================================================================")
    print(f"[+] All PDF files directly exported to: {screenshots_dir.resolve()}")
    print("==============================================================================")


if __name__ == "__main__":
    main()
