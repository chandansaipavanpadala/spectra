#!/usr/bin/env python3
"""
SPECTRA - Script 07: Real Vivado Hardware Synthesis Report Parser & Auditor
Ingests genuine post-synthesis Vivado reports in reports/:
  - vivado_utilization_golden.txt & vivado_utilization_trojan.txt
  - vivado_power_golden.txt       & vivado_power_trojan.txt
  - vivado_timing_golden.txt      & vivado_timing_trojan.txt
Zero hardcoded hardware metrics and zero fake report auto-generators.
Asserts trojan_luts > golden_luts and trojan_ffs > golden_ffs (confirming DONT_TOUCH).
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
REPORTS_DIR = REPO_ROOT / "reports"

GOLDEN_RTL = SRC_DIR / "aes_128.v"
TROJAN_RTL = SRC_DIR / "aes_128_trojan.v"

ARTIX7_LUT_CAP = 20800
ARTIX7_FF_CAP = 41600


def analyze_rtl_registers(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()
    reg_matches = re.findall(r"reg\s+(?:\[(\d+):(\d+)\])?\s*([a-zA-Z0-9_,\s]+);", code)
    total_ffs = 0
    signals = []
    for msb, lsb, names in reg_matches:
        width = 1 if msb == "" else (abs(int(msb) - int(lsb)) + 1)
        for v in [n.strip() for n in names.split(",") if n.strip()]:
            total_ffs += width
            signals.append((v, width))
    return total_ffs, signals


def parse_vivado_utilization(report_path):
    if not report_path.exists():
        raise FileNotFoundError(f"Run Vivado synthesis first! Missing utilization report: {report_path}")
    luts = ffs = iobs = None
    with open(report_path, "r", encoding="utf-8") as f:
        for line in f:
            if "Slice LUTs*" in line or re.match(r"^\|\s*Slice LUTs\s*\|", line):
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    luts = int(parts[1])
            elif re.match(r"^\|\s*Slice Registers\s*\|", line):
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    ffs = int(parts[1])
            elif re.match(r"^\|\s*Bonded IOB\s*\|", line):
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    iobs = int(parts[1])
    if luts is None or ffs is None:
        raise ValueError(f"Could not parse Slice LUTs / Slice Registers from {report_path}")
    return {"slice_luts": luts, "slice_ffs": ffs, "bonded_iob": iobs if iobs is not None else 0}


def parse_vivado_power(report_path):
    if not report_path.exists():
        raise FileNotFoundError(f"Run Vivado synthesis first! Missing power report: {report_path}")
    total_w = dyn_w = static_w = None
    with open(report_path, "r", encoding="utf-8") as f:
        for line in f:
            if "Total On-Chip Power (W)" in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                total_w = float(parts[1])
            elif re.match(r"^\|\s*Dynamic \(W\)\s*\|", line):
                parts = [p.strip() for p in line.split("|") if p.strip()]
                dyn_w = float(parts[1])
            elif re.match(r"^\|\s*Device Static \(W\)\s*\|", line):
                parts = [p.strip() for p in line.split("|") if p.strip()]
                static_w = float(parts[1])
    if total_w is None or dyn_w is None or static_w is None:
        raise ValueError(f"Could not parse power metrics from {report_path}")
    return {"total_power_mw": total_w * 1000.0, "dynamic_power_mw": dyn_w * 1000.0, "static_power_mw": static_w * 1000.0}


def parse_vivado_timing(report_path):
    if not report_path.exists():
        raise FileNotFoundError(f"Run Vivado synthesis first! Missing timing report: {report_path}")
    wns = None
    clock_period_ns = None
    with open(report_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if "WNS(ns)" in line and "TNS(ns)" in line:
            for j in range(i + 1, min(i + 5, len(lines))):
                vals = lines[j].strip().split()
                if vals and re.match(r"^-?\d+(\.\d+)?$", vals[0]):
                    wns = float(vals[0])
                    break
        if line.strip().startswith("clk ") and "{" in line:
            m = re.search(r"\}\s+(\d+\.\d+)\s+(\d+\.\d+)", line)
            if m:
                clock_period_ns = float(m.group(1))

    if wns is None or clock_period_ns is None:
        raise ValueError(f"Could not parse WNS or clock period from {report_path}")

    crit_delay_ns = max(0.001, clock_period_ns - wns)
    fmax_mhz = 1000.0 / crit_delay_ns
    return {
        "clock_period_ns": clock_period_ns,
        "wns_ns": wns,
        "critical_path_delay_ns": crit_delay_ns,
        "fmax_mhz": fmax_mhz,
    }


def main():
    print("[+] Executing SPECTRA Script 07: Real Vivado Utilization, Power & Timing Audit...")

    golden_ffs_rtl, g_sigs = analyze_rtl_registers(GOLDEN_RTL)
    trojan_ffs_rtl, t_sigs = analyze_rtl_registers(TROJAN_RTL)

    u_g = parse_vivado_utilization(REPORTS_DIR / "vivado_utilization_golden.txt")
    u_t = parse_vivado_utilization(REPORTS_DIR / "vivado_utilization_trojan.txt")
    p_g = parse_vivado_power(REPORTS_DIR / "vivado_power_golden.txt")
    p_t = parse_vivado_power(REPORTS_DIR / "vivado_power_trojan.txt")
    t_g = parse_vivado_timing(REPORTS_DIR / "vivado_timing_golden.txt")
    t_t = parse_vivado_timing(REPORTS_DIR / "vivado_timing_trojan.txt")

    # Verify Vivado DONT_TOUCH attribute preserved the Trojan netlist
    assert u_t["slice_luts"] > u_g["slice_luts"] and u_t["slice_ffs"] > u_g["slice_ffs"], (
        f"Vivado pruned the Trojan or stale reports are present! "
        f"Golden=({u_g['slice_luts']} LUTs, {u_g['slice_ffs']} FFs) vs "
        f"Trojan=({u_t['slice_luts']} LUTs, {u_t['slice_ffs']} FFs). "
        f"Run Vivado synthesis (scripts/run_vivado_full_flow.tcl) with updated DONT_TOUCH RTL first."
    )

    delta_luts = u_t["slice_luts"] - u_g["slice_luts"]
    delta_lut_pct = (delta_luts / u_g["slice_luts"]) * 100.0
    delta_ffs = u_t["slice_ffs"] - u_g["slice_ffs"]
    delta_ff_pct = (delta_ffs / u_g["slice_ffs"]) * 100.0
    delta_pwr_mw = p_t["dynamic_power_mw"] - p_g["dynamic_power_mw"]
    delta_pwr_pct = (delta_pwr_mw / max(p_g["dynamic_power_mw"], 1e-6)) * 100.0
    delta_delay_pct = ((t_t["critical_path_delay_ns"] - t_g["critical_path_delay_ns"]) / t_g["critical_path_delay_ns"]) * 100.0

    results = {
        "rtl_audit": {
            "golden_registers_count": golden_ffs_rtl,
            "trojan_registers_count": trojan_ffs_rtl,
            "delta_registers": trojan_ffs_rtl - golden_ffs_rtl,
            "trojan_extra_signals": [s for s in t_sigs if s not in g_sigs],
        },
        "devices": {
            "artix7": {
                "source": "Vivado local OOC synthesis (xc7a35tcsg324-1)",
                "part": "xc7a35tcsg324-1",
                "family": "Xilinx Artix-7 (28nm)",
                "golden": {
                    **u_g,
                    "lut_utilization_pct": (u_g["slice_luts"] / ARTIX7_LUT_CAP) * 100.0,
                    "ff_utilization_pct": (u_g["slice_ffs"] / ARTIX7_FF_CAP) * 100.0,
                    **p_g,
                    **t_g,
                },
                "trojan": {
                    **u_t,
                    "lut_utilization_pct": (u_t["slice_luts"] / ARTIX7_LUT_CAP) * 100.0,
                    "ff_utilization_pct": (u_t["slice_ffs"] / ARTIX7_FF_CAP) * 100.0,
                    **p_t,
                    **t_t,
                },
                "overhead": {
                    "delta_lut_count": delta_luts,
                    "delta_lut_pct": delta_lut_pct,
                    "delta_ff_count": delta_ffs,
                    "delta_ff_pct": delta_ff_pct,
                    "delta_dynamic_power_mw": delta_pwr_mw,
                    "delta_dynamic_power_pct": delta_pwr_pct,
                    "delta_delay_pct": delta_delay_pct,
                    "dont_touch_preserved": True,
                },
            },
            "spartan3e_literature": {
                "source": "He et al. IEEE JIOT 2024 reference literature",
                "part": "xc3s500e-4fg320",
                "family": "Xilinx Spartan-3E (90nm, He et al. Target)",
                "published_trojan_area_ratio_pct": 0.10,
            },
        },
    }

    json_path = REPORTS_DIR / "fpga_hardware_utilization.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 88)
    print("SPECTRA REAL VIVADO OOC SYNTHESIS & RESOURCE UTILIZATION AUDIT (xc7a35tcsg324-1)")
    print("=" * 88)
    print(f"| Slice LUTs     | Golden: {u_g['slice_luts']:5d} | Trojan: {u_t['slice_luts']:5d} | Delta: +{delta_luts} ({delta_lut_pct:+.4f}%) |")
    print(f"| Slice FFs      | Golden: {u_g['slice_ffs']:5d} | Trojan: {u_t['slice_ffs']:5d} | Delta: +{delta_ffs} ({delta_ff_pct:+.4f}%) |")
    print(f"| Bonded IOBs    | Golden: {u_g['bonded_iob']:5d} | Trojan: {u_t['bonded_iob']:5d} | Out-of-Context Mode   |")
    print(f"| Dynamic Power  | Golden: {p_g['dynamic_power_mw']:6.2f} mW | Trojan: {p_t['dynamic_power_mw']:6.2f} mW | Delta: {delta_pwr_mw:+.3f} mW ({delta_pwr_pct:+.2f}%) |")
    print(f"| Crit. Delay    | Golden: {t_g['critical_path_delay_ns']:6.3f} ns | Trojan: {t_t['critical_path_delay_ns']:6.3f} ns | Fmax: {t_t['fmax_mhz']:.2f} MHz      |")
    print("=" * 88)
    print(f"[+] Exported real parsed metrics to {json_path}")


if __name__ == "__main__":
    main()
