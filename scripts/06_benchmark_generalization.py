#!/usr/bin/env python3
"""
SPECTRA - Script 06: Multi-Threat Hardware Trojan Taxonomy Evaluation Suite
Evaluates generalization across three standard Trust-HUB threat classes:
  1. Benchmark Class A: AES-T100 / He et al. 2024 Type (Synchronous 2-Bit Counter)
  2. Benchmark Class B: AES-T400 Type (Combinational Comparator Trigger & Supply Droop)
  3. Benchmark Class C: AES-T800 Type (Sequential Time-Bomb State Leakage)
Uses shared spectra_signal_core.py with ZERO ground-truth label leakage.
"""

import json
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from spectra_signal_core import (
    load_vivado_csv_traces,
    synthesize_trace_from_vivado_csv,
    extract_ev_ahbe,
    run_unsupervised_pipeline,
)

REPO_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = REPO_ROOT / "reports"
SCREENSHOTS_DIR = REPO_ROOT / "screenshots"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

PVT_SIGMA = 0.06


def evaluate_benchmark(benchmark_type, vcc_g, tog_g, vcc_t, tog_t):
    print(f"\n[*] Benchmarking Threat Profile: {benchmark_type.upper()}...")

    X_train_list, raw_energy_train = [], []
    X_val_list, y_val_list = [], []

    for i in range(24):
        tr = synthesize_trace_from_vivado_csv(
            vcc_g, tog_g, is_trojan=False, chip_seed=i,
            snr_db=25.0, clk_drift_pct=0.2, pvt_sigma=PVT_SIGMA, benchmark_type=benchmark_type
        )
        ev, _, re, _ = extract_ev_ahbe(tr)
        X_train_list.append(ev); raw_energy_train.append(re)

    for i in range(24):
        tr = synthesize_trace_from_vivado_csv(
            vcc_g, tog_g, vcc_t_cycles=vcc_t, tog_t_cycles=tog_t,
            is_trojan=True, chip_seed=i + 50,
            snr_db=25.0, clk_drift_pct=0.2, pvt_sigma=PVT_SIGMA, benchmark_type=benchmark_type
        )
        ev, _, re, _ = extract_ev_ahbe(tr)
        X_train_list.append(ev); raw_energy_train.append(re)

    for i in range(12):
        tr = synthesize_trace_from_vivado_csv(
            vcc_g, tog_g, is_trojan=False, chip_seed=i + 200,
            snr_db=25.0, clk_drift_pct=0.2, pvt_sigma=PVT_SIGMA, benchmark_type=benchmark_type
        )
        ev, _, _, _ = extract_ev_ahbe(tr)
        X_val_list.append(ev); y_val_list.append(0)

    for i in range(12):
        tr = synthesize_trace_from_vivado_csv(
            vcc_g, tog_g, vcc_t_cycles=vcc_t, tog_t_cycles=tog_t,
            is_trojan=True, chip_seed=i + 250,
            snr_db=25.0, clk_drift_pct=0.2, pvt_sigma=PVT_SIGMA, benchmark_type=benchmark_type
        )
        ev, _, _, _ = extract_ev_ahbe(tr)
        X_val_list.append(ev); y_val_list.append(1)

    res = run_unsupervised_pipeline(
        np.array(X_train_list), np.array(raw_energy_train),
        np.array(X_val_list), np.array(y_val_list), use_entropy_fusion=True
    )

    print(f"    SEA Energy: Trojan = {res['sea_trojan_energy']:.4e}, Golden = {res['sea_golden_energy']:.4e} | Verified: {res['sea_verified']}")
    print(f"    Validation Accuracy: {res['accuracy']:.2f}% | FPR: {res['fpr']:.2f}% | Dynamic Margin: {res['sep_margin']:.2e}")

    return {
        "benchmark_type": benchmark_type,
        "sea_verified": res["sea_verified"],
        "sea_golden_energy": res["sea_golden_energy"],
        "sea_trojan_energy": res["sea_trojan_energy"],
        "pca_variance_explained_pct": res["pca_variance_explained_pct"],
        "fusion_weights": res["fusion_weights"],
        "confusion_matrix": res["confusion_matrix"],
        "accuracy_pct": res["accuracy"],
        "precision_pct": res["precision"],
        "recall_pct": res["recall"],
        "false_positive_rate_pct": res["fpr"],
        "false_negative_rate_pct": res["fnr"],
        "mean_rfd_golden": res["mean_rfd_g"],
        "mean_rfd_trojan": res["mean_rfd_t"],
        "dynamic_separation_margin": res["sep_margin"],
    }


def main():
    print("[+] Executing SPECTRA Script 06: Multi-Trojan Benchmark Validation...")
    tog_g, vcc_g, tog_t, vcc_t = load_vivado_csv_traces(
        REPORTS_DIR / "power_trace_golden.csv",
        REPORTS_DIR / "power_trace_trojan.csv",
    )

    benchmarks = ["aes_t100", "aes_t400", "aes_t800"]
    benchmark_names = {
        "aes_t100": "AES-T100 / He et al. (Synchronous 2-Bit Counter)",
        "aes_t400": "Trust-HUB AES-T400 (Combinational Comparator Trigger)",
        "aes_t800": "Trust-HUB AES-T800 (Sequential Time-Bomb State Leakage)",
    }

    all_results = {bm: evaluate_benchmark(bm, vcc_g, tog_g, vcc_t, tog_t) for bm in benchmarks}

    output_report = {
        "evaluation_scope": "Multi-Threat Hardware Trojan Taxonomy Evaluation",
        "inter_die_process_variation": "6% Inter-Die Gaussian PVT (sigma = 0.06)",
        "training_chips_per_benchmark": 48,
        "validation_chips_per_benchmark": 24,
        "benchmarks_evaluated": benchmark_names,
        "results": all_results,
    }

    report_path = REPORTS_DIR / "multi_benchmark_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(output_report, f, indent=2)
    print(f"\n[+] Serialized multi-benchmark report to {report_path}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), dpi=300)
    labels = ["AES-T100 (Sync.)", "AES-T400 (Comb.)", "AES-T800 (Seq.)"]
    accuracies = [all_results[b]["accuracy_pct"] for b in benchmarks]
    margins = [max(1.0, all_results[b]["dynamic_separation_margin"]) for b in benchmarks]
    colors = ['#107C41', '#0A192F', '#D97706']

    bars1 = ax1.bar(labels, accuracies, color=colors, width=0.45, edgecolor='black', linewidth=1.2, alpha=0.9)
    ax1.set_ylim(80, 110)
    ax1.set_title("Panel 1: Detection Accuracy across Threat Profiles", fontsize=11, fontweight='bold', pad=12)
    ax1.set_ylabel("Validation Accuracy (%)", fontsize=10, fontweight='bold')
    ax1.grid(axis='y', linestyle='--', alpha=0.5)
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2.0, yval + 1.2, f"{yval:.1f}%",
                 ha='center', va='bottom', fontsize=10, fontweight='bold')

    bars2 = ax2.bar(labels, margins, color=colors, width=0.45, edgecolor='black', linewidth=1.2, alpha=0.9)
    ax2.set_yscale('log')
    ax2.set_ylim(min(margins) * 0.5, max(margins) * 3.5)
    ax2.set_title(r"Panel 2: Dynamic Separation Margin ($R_{FD,T} / R_{FD,G}$)", fontsize=11, fontweight='bold', pad=12)
    ax2.set_ylabel("Dynamic Separation Margin (Log Scale)", fontsize=10, fontweight='bold')
    ax2.grid(axis='y', linestyle='--', alpha=0.5, which="both")
    for bar in bars2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2.0, yval * 1.15, f"{yval:.2e}",
                 ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.subplots_adjust(left=0.08, right=0.96, top=0.90, bottom=0.12, wspace=0.25)
    plot_path = SCREENSHOTS_DIR / "benchmark_comparison.png"
    plt.savefig(plot_path, dpi=300)
    plt.close()
    print(f"[+] Exported 300 DPI benchmark comparison figure to {plot_path}")


if __name__ == "__main__":
    main()
