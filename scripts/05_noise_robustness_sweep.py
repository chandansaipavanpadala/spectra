#!/usr/bin/env python3
"""
SPECTRA - Script 05: Process Variation, SNR Sensitivity & Clock Drift Stress Test
Reference Conformance: IEEE JIOT 2024 (Eq. 1 - Eq. 20)
Stress Test: Signal-to-Noise Ratio (30 dB -> 5 dB) & Clock Drift (0.0% -> 3.0%)
Evaluation: Method A (Baseline He et al. 2024 Single-Bin) vs. Method B (SPECTRA AHBE)
Uses shared spectra_signal_core.py with ZERO ground-truth y_train label leakage.
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
    FS, F_CLK_NOM, N_SAMPLES,
    load_vivado_csv_traces,
    synthesize_trace_from_vivado_csv,
    extract_ev_both,
    run_unsupervised_pipeline,
)

REPO_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = REPO_ROOT / "reports"
SCREENSHOTS_DIR = REPO_ROOT / "screenshots"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

N_TRAIN_GOLDEN = 24
N_TRAIN_TROJAN = 24
N_VAL_GOLDEN = 12
N_VAL_TROJAN = 12
PVT_SIGMA = 0.06


def evaluate_condition(vcc_g, tog_g, vcc_t, tog_t, snr_db, drift_pct):
    xa_tr, xb_tr, ea_tr, eb_tr = [], [], [], []
    xa_val, xb_val, y_val = [], [], []

    # Exact 0.0% drift when locked (no crystal jitter), otherwise include +/-0.02% die-level variance
    def _die_drift(seed_val):
        if drift_pct == 0.0:
            return 0.0
        return drift_pct + np.random.RandomState(seed_val).normal(0.0, 0.02)

    for i in range(N_TRAIN_GOLDEN):
        tr = synthesize_trace_from_vivado_csv(vcc_g, tog_g, is_trojan=False, chip_seed=i,
                                              snr_db=snr_db, clk_drift_pct=_die_drift(1000 + i), pvt_sigma=PVT_SIGMA)
        ea, re_a, eb, re_b = extract_ev_both(tr)
        xa_tr.append(ea); xb_tr.append(eb); ea_tr.append(re_a); eb_tr.append(re_b)

    for i in range(N_TRAIN_TROJAN):
        tr = synthesize_trace_from_vivado_csv(vcc_g, tog_g, vcc_t_cycles=vcc_t, tog_t_cycles=tog_t,
                                              is_trojan=True, chip_seed=i + 50,
                                              snr_db=snr_db, clk_drift_pct=_die_drift(2000 + i), pvt_sigma=PVT_SIGMA)
        ea, re_a, eb, re_b = extract_ev_both(tr)
        xa_tr.append(ea); xb_tr.append(eb); ea_tr.append(re_a); eb_tr.append(re_b)

    for i in range(N_VAL_GOLDEN):
        tr = synthesize_trace_from_vivado_csv(vcc_g, tog_g, is_trojan=False, chip_seed=i + 200,
                                              snr_db=snr_db, clk_drift_pct=_die_drift(3000 + i), pvt_sigma=PVT_SIGMA)
        ea, _, eb, _ = extract_ev_both(tr)
        xa_val.append(ea); xb_val.append(eb); y_val.append(0)

    for i in range(N_VAL_TROJAN):
        tr = synthesize_trace_from_vivado_csv(vcc_g, tog_g, vcc_t_cycles=vcc_t, tog_t_cycles=tog_t,
                                              is_trojan=True, chip_seed=i + 250,
                                              snr_db=snr_db, clk_drift_pct=_die_drift(4000 + i), pvt_sigma=PVT_SIGMA)
        ea, _, eb, _ = extract_ev_both(tr)
        xa_val.append(ea); xb_val.append(eb); y_val.append(1)

    y_val = np.array(y_val)
    res_a = run_unsupervised_pipeline(np.array(xa_tr), np.array(ea_tr), np.array(xa_val), y_val, use_entropy_fusion=False)
    res_b = run_unsupervised_pipeline(np.array(xb_tr), np.array(eb_tr), np.array(xb_val), y_val, use_entropy_fusion=True)
    return res_a, res_b


def main():
    print("[+] Executing SPECTRA Script 05: PVT, SNR & Clock Drift Stress Test...")
    tog_g, vcc_g, tog_t, vcc_t = load_vivado_csv_traces(
        REPORTS_DIR / "power_trace_golden.csv",
        REPORTS_DIR / "power_trace_trojan.csv",
    )

    snr_levels = [30, 25, 20, 15, 10, 5]
    drift_levels = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

    # Experiment 1: SNR Sensitivity Sweep (30 dB -> 5 dB, Drift = 0.5%)
    print("[*] Experiment 1: Evaluating SNR Sweep (30 dB -> 5 dB, Drift = 0.5%, PVT = 6%)...")
    snr_results = {
        "snr_db": snr_levels,
        "method_a_he": {"accuracy": [], "fpr": [], "fnr": [], "sep_margin": []},
        "method_b_spectra": {"accuracy": [], "fpr": [], "fnr": [], "sep_margin": []},
    }

    for snr in snr_levels:
        res_a, res_b = evaluate_condition(vcc_g, tog_g, vcc_t, tog_t, snr_db=snr, drift_pct=0.5)
        for key, res in [("method_a_he", res_a), ("method_b_spectra", res_b)]:
            snr_results[key]["accuracy"].append(res["accuracy"])
            snr_results[key]["fpr"].append(res["fpr"])
            snr_results[key]["fnr"].append(res["fnr"])
            snr_results[key]["sep_margin"].append(res["sep_margin"])
        print(f"    SNR={snr:2d} dB | He: Acc {res_a['accuracy']:5.1f}% (FPR {res_a['fpr']:4.1f}%) "
              f"| SPECTRA: Acc {res_b['accuracy']:5.1f}% (FPR {res_b['fpr']:4.1f}%, Margin {res_b['sep_margin']:.2e})")

    # Experiment 2: Clock Drift Sweep (0.0% -> 3.0%, SNR = 30 dB)
    print("[*] Experiment 2: Evaluating Clock Drift Sweep (0.0% -> 3.0%, SNR = 30 dB, PVT = 6%)...")
    drift_results = {
        "drift_pct": drift_levels,
        "method_a_he": {"accuracy": [], "fpr": [], "fnr": [], "sep_ratio_t": [], "sep_ratio_g": [], "sep_margin": []},
        "method_b_spectra": {"accuracy": [], "fpr": [], "fnr": [], "sep_ratio_t": [], "sep_ratio_g": [], "sep_margin": []},
    }

    for drift in drift_levels:
        res_a, res_b = evaluate_condition(vcc_g, tog_g, vcc_t, tog_t, snr_db=30.0, drift_pct=drift)
        for key, res in [("method_a_he", res_a), ("method_b_spectra", res_b)]:
            drift_results[key]["accuracy"].append(res["accuracy"])
            drift_results[key]["fpr"].append(res["fpr"])
            drift_results[key]["fnr"].append(res["fnr"])
            drift_results[key]["sep_ratio_t"].append(res["mean_rfd_t"])
            drift_results[key]["sep_ratio_g"].append(res["mean_rfd_g"])
            drift_results[key]["sep_margin"].append(res["sep_margin"])
        print(f"    Drift={drift:3.1f}% | He: Acc {res_a['accuracy']:5.1f}% (Margin {res_a['sep_margin']:.2e}) "
              f"| SPECTRA: Acc {res_b['accuracy']:5.1f}% (Margin {res_b['sep_margin']:.2e})")

    full_report = {
        "sweep_configuration": {
            "sampling_frequency_hz": FS,
            "nominal_clock_hz": F_CLK_NOM,
            "sample_points": N_SAMPLES,
            "training_chips": N_TRAIN_GOLDEN + N_TRAIN_TROJAN,
            "validation_chips": N_VAL_GOLDEN + N_VAL_TROJAN,
            "pvt_process_variation_sigma": PVT_SIGMA,
            "ahbe_bandwidth_khz": 1000.0,
            "window_half_width_khz": 500.0,
        },
        "snr_sensitivity_sweep": snr_results,
        "clock_drift_sweep": drift_results,
    }

    report_path = REPORTS_DIR / "noise_robustness_results.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)
    print(f"[+] Serialized sensitivity results to {report_path}")

    # Dual-Panel Publication Plot with Legends Placed Cleanly Outside Data Regions
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6.0), dpi=300)

    ax1.plot(snr_levels, snr_results["method_b_spectra"]["accuracy"], 's-', color='#107C41',
             linewidth=2.4, markersize=8, label='SPECTRA (AHBE Bands)')
    ax1.plot(snr_levels, snr_results["method_a_he"]["accuracy"], 'o--', color='#C0392B',
             linewidth=2.0, markersize=8, label='Baseline He et al. (Single-Bin)')
    ax1.axhline(100.0, color='#0A192F', linestyle=':', alpha=0.6, linewidth=1.0)
    ax1.set_title("Panel 1: Accuracy vs. SNR (at 0.5% Clock Drift & 6% PVT)", fontsize=11, fontweight='bold', pad=34)
    ax1.set_xlabel("Signal-to-Noise Ratio (SNR in dB)", fontsize=10, fontweight='bold')
    ax1.set_ylabel("Detection Accuracy (%)", fontsize=10, fontweight='bold')
    ax1.set_ylim(25, 108)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2, frameon=True, fontsize=8.8)

    ax2.plot(drift_levels, drift_results["method_b_spectra"]["sep_margin"], 's-', color='#0A192F',
             linewidth=2.4, markersize=8, label=r'SPECTRA AHBE ($R_{FD,T} / R_{FD,G}$)')
    ax2.plot(drift_levels, drift_results["method_a_he"]["sep_margin"], '^--', color='#D97706',
             linewidth=2.0, markersize=8, label=r'Baseline He et al. ($R_{FD,T} / R_{FD,G}$)')
    ax2.set_yscale('log')
    ax2.set_title(r"Panel 2: Dynamic Separation Ratio vs. Clock Drift ($\pm \%$)", fontsize=11, fontweight='bold', pad=34)
    ax2.set_xlabel(r"Clock Frequency Drift $\Delta f_{\mathrm{clk}}$ ($\pm \%$)", fontsize=10, fontweight='bold')
    ax2.set_ylabel("Dynamic Separation Ratio (Log Scale)", fontsize=10, fontweight='bold')
    ax2.grid(True, linestyle="--", alpha=0.5, which="both")
    ax2.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2, frameon=True, fontsize=8.8)

    plt.tight_layout()
    plot_path = SCREENSHOTS_DIR / "noise_robustness_sweep.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[+] Exported 300 DPI publication figure to {plot_path}")


if __name__ == "__main__":
    main()
