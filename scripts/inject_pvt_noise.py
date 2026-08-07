#!/usr/bin/env python3
"""
==================================================================================
Script: inject_pvt_noise.py
Description: PVT (Process, Voltage, Temperature) Noise Simulator.
             Injects supply voltage drift (Vdd +- 5%) and Gaussian thermal jitter
             (sigma = 2.0) into runtime RO sensor telemetry to stress-test ML classifiers.
Physical Hardware Noise & Reliability Simulator
==================================================================================
"""

import argparse
import csv
import math
import random
import sys
from pathlib import Path


def inject_pvt_noise(input_path: Path, output_path: Path, vdd_drift: float, thermal_jitter: float, seed: int):
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
        # Low frequency random walk / sinusoidal drift
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

    inject_pvt_noise(input_path, output_path, args.vdd_drift, args.thermal_jitter, args.seed)


if __name__ == "__main__":
    main()
