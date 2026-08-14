#!/usr/bin/env python3
"""
==================================================================================
Script: inject_pvt_noise.py
Description: PVT (Process, Voltage, Temperature) Noise Simulator.
             Injects supply voltage drift (Vdd +- 5%) and Gaussian thermal jitter
             (sigma = 2.0) into runtime RO sensor telemetry to stress-test ML classifiers.
             Exports waveform comparison plots directly into screenshots/ directory.
Physical Hardware Noise & Reliability Simulator
==================================================================================
"""

import argparse
import csv
import math
import random
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def export_pvt_noise_screenshots(rows_clean, rows_noisy, vdd_drift, thermal_jitter, screenshots_dir: Path):
    """
    Export clean vs noisy telemetry frequency waveform plot to screenshots/ directory.
    """
    if not HAS_PIL:
        return

    screenshots_dir.mkdir(parents=True, exist_ok=True)
    out_file = screenshots_dir / "inject_pvt_noise_telemetry_waveforms.png"

    width, height = 1100, 650
    img = Image.new("RGB", (width, height), "#1E1E2E")
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([0, 0, width, 80], fill="#181825")
    draw.text((40, 20), "PVT NOISE INJECTION: CLEAN VS NOISY SENSOR TELEMETRY", fill="#F5E0DC", font_size=22)
    draw.text((40, 50), f"Supply Voltage Drift: Vdd +/- {vdd_drift*100:.1f}% | Thermal Jitter: sigma = {thermal_jitter}", fill="#BAC2DE", font_size=13)

    # Chart Canvas
    chart_x, chart_y = 60, 110
    chart_w, chart_h = 980, 480
    draw.rectangle([chart_x, chart_y, chart_x + chart_w, chart_y + chart_h], fill="#181825", outline="#45475A", width=2)

    n_pts = min(len(rows_clean), len(rows_noisy))
    if n_pts < 2:
        img.save(out_file, "PNG", dpi=(300, 300))
        return

    # Extract series
    c_ro1 = [float(r["ro1_freq"]) for r in rows_clean[:n_pts]]
    c_ro2 = [float(r["ro2_freq"]) for r in rows_clean[:n_pts]]
    n_ro1 = [r["ro1_freq"] for r in rows_noisy[:n_pts]]
    n_ro2 = [r["ro2_freq"] for r in rows_noisy[:n_pts]]

    all_vals = c_ro1 + c_ro2 + n_ro1 + n_ro2
    max_v = max(all_vals) if all_vals else 100.0
    min_v = min(all_vals) if all_vals else 0.0
    v_range = max(1.0, max_v - min_v)

    def to_coords(idx, val):
        x = chart_x + int((idx / (n_pts - 1)) * (chart_w - 40)) + 20
        y = chart_y + chart_h - 20 - int(((val - min_v) / v_range) * (chart_h - 60))
        return x, y

    # Draw grid lines
    for grid_v in range(4):
        gy = chart_y + 30 + grid_v * (chart_h // 4)
        draw.line([chart_x + 10, gy, chart_x + chart_w - 10, gy], fill="#313244", width=1)

    # Plot lines
    # Clean RO1 (Blue)
    pts_c1 = [to_coords(i, v) for i, v in enumerate(c_ro1)]
    for i in range(len(pts_c1) - 1):
        draw.line([pts_c1[i], pts_c1[i+1]], fill="#89B4FA", width=2)

    # Noisy RO1 (Red Jitter)
    pts_n1 = [to_coords(i, v) for i, v in enumerate(n_ro1)]
    for i in range(len(pts_n1) - 1):
        draw.line([pts_n1[i], pts_n1[i+1]], fill="#F38BA8", width=2)

    # Legend
    draw.rectangle([chart_x + 30, chart_y + 20, chart_x + 320, chart_y + 80], fill="#313244", outline="#45475A", width=1)
    draw.line([chart_x + 40, chart_y + 40, chart_x + 70, chart_y + 40], fill="#89B4FA", width=3)
    draw.text((chart_x + 80, chart_y + 33), "Clean Baseline RO1", fill="#CDD6F4", font_size=12)

    draw.line([chart_x + 40, chart_y + 60, chart_x + 70, chart_y + 60], fill="#F38BA8", width=3)
    draw.text((chart_x + 80, chart_y + 53), "Noisy Telemetry RO1 (PVT)", fill="#CDD6F4", font_size=12)

    img.save(out_file, "PNG", dpi=(300, 300))
    print(f"[+] Saved PVT Noise Telemetry plot to: {out_file}")


def inject_pvt_noise(input_path: Path, output_path: Path, vdd_drift: float, thermal_jitter: float, seed: int, screenshots_dir: Path):
    """
    Read CSV sensor telemetry and apply Vdd supply drift and thermal Gaussian noise.
    """
    if not input_path.exists():
        print(f"[-] Error: Input telemetry file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    random.seed(seed)

    rows = []
    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean_row = {k.strip(): v.strip() for k, v in row.items()}
            rows.append(clean_row)

    if not rows:
        print(f"[-] Error: Telemetry file '{input_path}' is empty.", file=sys.stderr)
        sys.exit(1)

    noisy_rows = []
    for r in rows:
        ts = r["timestamp"]
        test_mode = int(float(r["test_mode"]))
        ro1_clean = float(r["ro1_freq"])
        ro2_clean = float(r["ro2_freq"])

        # 1. Supply Voltage Drift (Vdd +- 5%) -> Proportional Frequency Shift
        v_factor = 1.0 + random.uniform(-vdd_drift, vdd_drift)

        # 2. Gaussian Thermal / High-Frequency Jitter (sigma)
        jitter_ro1 = random.gauss(0.0, thermal_jitter)
        jitter_ro2 = random.gauss(0.0, thermal_jitter)

        # Apply PVT effects
        ro1_noisy = round(max(0.0, (ro1_clean * v_factor) + jitter_ro1), 2)
        ro2_noisy = round(max(0.0, (ro2_clean * v_factor) + jitter_ro2), 2)
        delta_noisy = round(abs(ro1_noisy - ro2_noisy), 2)

        noisy_rows.append({
            "timestamp": ts,
            "test_mode": test_mode,
            "ro1_freq": ro1_noisy,
            "ro2_freq": ro2_noisy,
            "freq_delta": delta_noisy
        })

    # Save to Output CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["timestamp", "test_mode", "ro1_freq", "ro2_freq", "freq_delta"]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(noisy_rows)

    # Print Summary Statistics
    print("\n" + "=" * 78)
    print("           PVT ENVIRONMENTAL NOISE SIMULATION SUMMARY")
    print("=" * 78)
    print(f" Input Telemetry Log       : {input_path}")
    print(f" Output Noisy Log          : {output_path}")
    print(f" Processed Samples         : {len(noisy_rows)}")
    print(f" Supply Voltage Drift (Vdd): +/- {vdd_drift * 100:.1f}%")
    print(f" Thermal Gaussian Jitter   : sigma = {thermal_jitter}")
    print("-" * 78)
    print(f" Sample Clean vs Noisy Comparison (First Row):")
    print(f"   Clean  -> RO1: {rows[0]['ro1_freq']}, RO2: {rows[0]['ro2_freq']}, Delta: {rows[0]['freq_delta']}")
    print(f"   Noisy  -> RO1: {noisy_rows[0]['ro1_freq']}, RO2: {noisy_rows[0]['ro2_freq']}, Delta: {noisy_rows[0]['freq_delta']}")
    print("=" * 78 + "\n")

    # Export Visualization Plot directly to screenshots/
    export_pvt_noise_screenshots(rows, noisy_rows, vdd_drift, thermal_jitter, screenshots_dir)


def main():
    parser = argparse.ArgumentParser(
        description="PVT Environmental Noise & Jitter Simulation Engine"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="reports/runtime_sensor_data.csv",
        help="Path to clean input sensor CSV (default: reports/runtime_sensor_data.csv)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/runtime_sensor_data_pvt.csv",
        help="Path to output noisy sensor CSV (default: reports/runtime_sensor_data_pvt.csv)"
    )
    parser.add_argument(
        "--vdd-drift",
        type=float,
        default=0.05,
        help="Maximum Vdd supply voltage drift percentage (default: 0.05 -> +-5%)"
    )
    parser.add_argument(
        "--thermal-jitter",
        type=float,
        default=2.0,
        help="Standard deviation of Gaussian thermal jitter (default: 2.0)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic noise generation (default: 42)"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    screenshots_dir = Path("screenshots")

    inject_pvt_noise(input_path, output_path, args.vdd_drift, args.thermal_jitter, args.seed, screenshots_dir)


if __name__ == "__main__":
    main()
