#!/usr/bin/env python3
"""
==================================================================================
Script: parse_rare_nets.py
Description: Parses VCD simulation waveform traces to extract signal switching
             activity, calculates switching probabilities (P_s), and flags
             High-Risk Rare Nets (P_s < threshold) for hardware security analysis.
IEEE 1364-2001 VCD Trace Parser for Pre-Silicon Security & Side-Channel Analysis
==================================================================================
"""

import argparse
import json
import re
import sys
from pathlib import Path


def parse_vcd(vcd_path: Path):
    """
    Parse VCD file to extract signals, bit-level toggle counts, and clock cycles.
    """
    id_to_info = {}       # id -> {'name': full_name, 'size': int}
    id_to_value = {}      # id -> current_value_string
    id_to_toggles = {}    # id -> int (total bit toggles)

    scope_stack = []
    clk_id = None
    clk_rising_edges = 0
    in_header = True

    current_time = 0
    start_time = None
    end_time = 0

    with open(vcd_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Header parsing
            if in_header:
                if line.startswith("$scope"):
                    parts = line.split()
                    if len(parts) >= 3:
                        scope_stack.append(parts[2])
                elif line.startswith("$upscope"):
                    if scope_stack:
                        scope_stack.pop()
                elif line.startswith("$var"):
                    parts = line.split()
                    # $var <type> <size> <id> <name> [<slice>] $end
                    if len(parts) >= 5:
                        var_size = int(parts[2])
                        var_id = parts[3]
                        var_name = parts[4]
                        
                        # Include slice if present in name or extra argument
                        if len(parts) > 6 and parts[5] != "$end":
                            var_name = f"{var_name}{parts[5]}"

                        full_name = ".".join(scope_stack + [var_name])
                        
                        id_to_info[var_id] = {"name": full_name, "size": var_size}
                        id_to_toggles[var_id] = 0
                        id_to_value[var_id] = "x" * var_size

                        # Identify main clock net if named clk
                        if var_name == "clk" or full_name.endswith(".clk"):
                            clk_id = var_id

                elif "$enddefinitions" in line:
                    in_header = False
                continue

            # Simulation Value Change Section
            if line.startswith("#"):
                try:
                    current_time = int(line[1:])
                    if start_time is None:
                        start_time = current_time
                    end_time = current_time
                except ValueError:
                    pass
                continue

            # Scalar value change (0!, 1!, x!, z!)
            if line[0] in ("0", "1", "x", "X", "z", "Z") and len(line) > 1 and not line.startswith("$"):
                val = line[0]
                var_id = line[1:]

                if var_id in id_to_info:
                    old_val = id_to_value.get(var_id, "x")
                    if old_val != "x" and old_val != "X" and val != old_val and val in ("0", "1"):
                        id_to_toggles[var_id] += 1

                    # Track clock rising edges
                    if var_id == clk_id and old_val == "0" and val == "1":
                        clk_rising_edges += 1

                    id_to_value[var_id] = val

            # Vector value change (b1010 !, B1010 !)
            elif (line.startswith("b") or line.startswith("B")) and " " in line:
                parts = line.split()
                if len(parts) >= 2:
                    raw_val = parts[0][1:]  # strip 'b' prefix
                    var_id = parts[1]

                    if var_id in id_to_info:
                        size = id_to_info[var_id]["size"]
                        # Zero-pad or expand to full bit width
                        bin_val = raw_val.zfill(size)[-size:]
                        old_bin_val = id_to_value.get(var_id, "x" * size)

                        # Count bit-level toggles
                        if old_bin_val != "x" * size:
                            toggles = 0
                            for b_old, b_new in zip(old_bin_val, bin_val):
                                if b_old in ("0", "1") and b_new in ("0", "1") and b_old != b_new:
                                    toggles += 1
                            id_to_toggles[var_id] += toggles

                        id_to_value[var_id] = bin_val

    # Total clock cycles determination
    if clk_rising_edges > 0:
        total_cycles = clk_rising_edges
    else:
        # Fallback: Estimate cycles from timeframe assuming 10ns clock period (100MHz)
        total_time = (end_time - start_time) if start_time is not None else 0
        total_cycles = max(1, total_time // 10)

    return id_to_info, id_to_toggles, total_cycles


def analyze_switching_activity(id_to_info, id_to_toggles, total_cycles, threshold):
    """
    Calculate switching probability for each net and identify High-Risk Rare Nets.
    """
    net_stats = []

    for var_id, info in id_to_info.items():
        name = info["name"]
        size = info["size"]
        toggles = id_to_toggles.get(var_id, 0)

        # Switching Probability = Total Toggles / Total Clock Cycles
        prob = toggles / total_cycles if total_cycles > 0 else 0.0
        prob_rounded = round(prob, 6)

        net_stats.append({
            "net_name": name,
            "size": size,
            "toggles": toggles,
            "switching_prob": prob_rounded,
            "is_rare": prob_rounded < threshold
        })

    return net_stats


def main():
    parser = argparse.ArgumentParser(
        description="VCD Trace Rare-Net Parser & Switching Activity Analyzer"
    )
    parser.add_argument(
        "--vcd",
        type=str,
        default="reports/sim_output.vcd",
        help="Path to input VCD waveform file (default: reports/sim_output.vcd)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.05,
        help="Switching probability threshold for rare nets (default: 0.05)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/rare_nets_profile.json",
        help="Path to output JSON rare nets profile (default: reports/rare_nets_profile.json)",
    )

    args = parser.parse_args()

    vcd_path = Path(args.vcd)
    output_path = Path(args.output)

    if not vcd_path.exists():
        print(f"[-] Error: Input VCD file '{vcd_path}' not found.", file=sys.stderr)
        sys.exit(1)

    # Parse VCD Trace
    print(f"[+] Parsing VCD trace file: {vcd_path}")
    id_to_info, id_to_toggles, total_cycles = parse_vcd(vcd_path)

    # Compute Switching Activity Statistics
    net_stats = analyze_switching_activity(id_to_info, id_to_toggles, total_cycles, args.threshold)
    
    total_nets = len(net_stats)
    rare_nets = [n for n in net_stats if n["is_rare"]]
    rare_nets_count = len(rare_nets)

    # Sort nets by switching probability
    sorted_by_activity = sorted(net_stats, key=lambda x: x["switching_prob"], reverse=True)

    top_5_active = sorted_by_activity[:5]
    top_5_dormant = sorted_by_activity[-5:]

    # Terminal Output Summary
    print("\n" + "=" * 78)
    print("           VCD SIGNAL SWITCHING ACTIVITY & RARE NETS ANALYSIS")
    print("=" * 78)
    print(f" Total Analyzed Signal Nets  : {total_nets}")
    print(f" Total Simulation Clock Cycles: {total_cycles}")
    print(f" Switching Probability Thresh: < {args.threshold * 100:.1f}% ({args.threshold})")
    print(f" Identified High-Risk Rare Nets: {rare_nets_count} / {total_nets}")
    print("-" * 78)

    print("\n[ TOP 5 MOST ACTIVE / FREQUENTLY TOGGLED NETS ]")
    print(f" {'Net Name':<45} | {'Toggles':<8} | {'Prob (P_s)':<10}")
    print(" " + "-" * 70)
    for net in top_5_active:
        print(f" {net['net_name']:<45} | {net['toggles']:<8} | {net['switching_prob']:<10.6f}")

    print("\n[ TOP 5 MOST DORMANT / RARE-SWITCHING NETS ]")
    print(f" {'Net Name':<45} | {'Toggles':<8} | {'Prob (P_s)':<10}")
    print(" " + "-" * 70)
    for net in top_5_dormant:
        print(f" {net['net_name']:<45} | {net['toggles']:<8} | {net['switching_prob']:<10.6f}")
    print("=" * 78 + "\n")

    # Generate Output JSON Profile
    json_output = {
        "summary": {
            "total_nets": total_nets,
            "rare_nets_count": rare_nets_count,
            "threshold": args.threshold,
        },
        "rare_nets": [
            {
                "net_name": n["net_name"],
                "toggles": n["toggles"],
                "switching_prob": n["switching_prob"],
                "risk_level": "HIGH",
            }
            for n in rare_nets
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2)

    print(f"[+] Rare nets profile successfully exported to: {output_path}")


if __name__ == "__main__":
    main()
