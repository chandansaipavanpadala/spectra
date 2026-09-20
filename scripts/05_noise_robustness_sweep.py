#!/usr/bin/env python3
"""
SPECTRA - Script 05: Process Variation & SNR Sensitivity Sweep
Reference Conformance: IEEE JIOT 2024 (Eq. 1 - Eq. 20)
Stress Test: Signal-to-Noise Ratio (30 dB -> 5 dB) & Clock Drift (0.0% -> 3.0%)
Evaluation: Method A (Baseline He et al.) vs. Method B (SPECTRA AHBE)
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# Repository Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
SCREENSHOTS_DIR = REPO_ROOT / "screenshots"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Fixed Experimental Parameters
FS = 2.5e9           # Sampling frequency: 2.5 GHz
F_CLK_NOM = 10e6     # Nominal clock frequency: 10 MHz
N_SAMPLES = 1000000  # 1,000,000 points
N_CHIPS_GOLDEN = 24
N_CHIPS_TROJAN = 24
TOTAL_CHIPS = N_CHIPS_GOLDEN + N_CHIPS_TROJAN

# Frequency grids for 129-D feature vector
SUB_HARMONICS = np.linspace(0, F_CLK_NOM, 65)
HARMONICS = np.linspace(F_CLK_NOM + 5e6, 640e6, 64)
TARGET_FREQS = np.concatenate([SUB_HARMONICS, HARMONICS])

def generate_chip_trace(is_trojan=False, snr_db=20.0, clk_drift_pct=0.0, chip_id=0):
    """
    Synthesize time-domain power proxy trace d[t] with calibrated SNR and clock drift.
    """
    np.random.seed(chip_id * 37 + (5000 if is_trojan else 100))
    t = np.arange(N_SAMPLES) / FS

    # Actual clock frequency under thermal drift / phase jitter
    f_clk = F_CLK_NOM * (1.0 + clk_drift_pct / 100.0)

    # Core switching clock harmonics (10 MHz fundamental + harmonics)
    signal = (
        0.80 * np.sin(2 * np.pi * f_clk * t) +
        0.40 * np.sin(2 * np.pi * (2 * f_clk) * t) +
        0.20 * np.sin(2 * np.pi * (3 * f_clk) * t) +
        0.10 * np.sin(2 * np.pi * (4 * f_clk) * t)
    )

    # Inter-die process variation (slow envelope modulation)
    pvt_drift = 0.05 * np.sin(2 * np.pi * 50e3 * t) + np.random.normal(0, 0.003, N_SAMPLES)
    signal += pvt_drift

    # Hardware Trojan localized capacitive switching (inter-harmonics at 1.5, 2.5, 3.5 * f_clk)
    if is_trojan:
        trojan_leakage = (
            0.25 * np.sin(2 * np.pi * (1.5 * f_clk) * t) +
            0.18 * np.cos(2 * np.pi * (2.5 * f_clk) * t) +
            0.12 * np.sin(2 * np.pi * (3.5 * f_clk) * t)
        )
        signal += trojan_leakage

    # Compute signal power and inject additive Gaussian noise calibrated to SNR (dB)
    p_signal = np.mean(signal ** 2)
    noise_variance = p_signal / (10.0 ** (snr_db / 10.0))
    noise = np.random.normal(0, np.sqrt(noise_variance), N_SAMPLES)

    trace = signal + noise
    return trace

def extract_eigenvectors_both_methods(trace):
    """
    Extracts 129-D feature vectors using:
    - Method A: Baseline He et al. (single-bin discrete sampling)
    - Method B: SPECTRA AHBE (continuous band integration +/- 500 kHz)
    Returns normalized feature vectors and raw total spectral energy for SEA.
    """
    fft_vals = np.fft.fftshift(np.fft.fft(trace, n=N_SAMPLES))
    pos_spectrum = np.abs(fft_vals[500000:1000000]) # 0 to 1.25 GHz
    raw_energy = float(np.sum(pos_spectrum ** 2))
    n_pos = len(pos_spectrum)

    # Bin indices for nominal target frequencies
    sampled_indices = np.clip((TARGET_FREQS / (FS / 2.0) * (n_pos - 1)).astype(int), 0, n_pos - 1)

    # Method A: Discrete single-bin sampling (He et al. 2024 Eq. 3)
    ev_a = pos_spectrum[sampled_indices].copy()
    ev_a = ev_a / (np.linalg.norm(ev_a) + 1e-12)

    # Method B: Adaptive Harmonic Band Energy (AHBE) (+/- 500 kHz band)
    window_half_width = max(1, int(500e3 / (FS / 2.0) * n_pos))
    ev_b = np.zeros(129)
    for i, idx in enumerate(sampled_indices):
        start_w = max(0, idx - window_half_width)
        end_w = min(n_pos, idx + window_half_width + 1)
        ev_b[i] = np.sqrt(np.mean(pos_spectrum[start_w:end_w] ** 2))
    ev_b = ev_b / (np.linalg.norm(ev_b) + 1e-12)

    return ev_a, ev_b, raw_energy

def run_fcm_sea_pca_classifier(X, true_labels, raw_energies):
    """
    Executes the full downstream SPECTRA pipeline:
    FCM (c=2, m=2.0) -> SEA labeling -> 10-D PCA -> Entropy-Weighted Distance Fusion
    Returns accuracy (%), FPR (%), mean_Rfd_G, mean_Rfd_T, and separation margin.
    """
    n_samples, n_features = X.shape
    c = 2
    m = 2.0

    # Initialize FCM membership matrix
    np.random.seed(42)
    U = np.random.dirichlet(np.ones(c), size=n_samples)

    for _ in range(50):
        U_prev = U.copy()
        Um = U ** m
        V = (Um.T @ X) / (np.sum(Um, axis=0)[:, np.newaxis] + 1e-12)

        D_mat = np.zeros((n_samples, c))
        for j in range(c):
            D_mat[:, j] = np.linalg.norm(X - V[j], axis=1)
        D_mat = np.maximum(D_mat, 1e-12)

        power_exp = 2.0 / (m - 1.0)
        for j in range(c):
            denom = np.sum((D_mat[:, j:j+1] / D_mat) ** power_exp, axis=1)
            U[:, j] = 1.0 / (denom + 1e-12)

        if np.max(np.abs(U - U_prev)) < 1e-5:
            break

    # Spectral Energy Analysis (SEA) cluster identification (Eq. 13)
    # Energy integral int |V_T|^2 df > int |V_G|^2 df
    Um = U ** m
    e_c0 = np.sum(Um[:, 0] * raw_energies) / np.sum(Um[:, 0])
    e_c1 = np.sum(Um[:, 1] * raw_energies) / np.sum(Um[:, 1])

    if e_c0 >= e_c1:
        v_trojan = V[0]
        v_golden = V[1]
    else:
        v_trojan = V[1]
        v_golden = V[0]

    # PCA 10-D projection
    X_mean = np.mean(X, axis=0)
    X_centered = X - X_mean
    cov_matrix = np.cov(X_centered, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
    sorted_idx = np.argsort(eigenvalues)[::-1]
    k_comp = min(10, n_samples - 1)
    coeff = eigenvectors[:, sorted_idx[:k_comp]]

    scores = X_centered @ coeff
    mu_g_10 = (v_golden - X_mean) @ coeff
    mu_t_10 = (v_trojan - X_mean) @ coeff

    sc_g = scores[true_labels == 0]
    sc_t = scores[true_labels == 1]
    cov_g_10 = np.cov(sc_g, rowvar=False) + 1e-6 * np.eye(k_comp)
    cov_t_10 = np.cov(sc_t, rowvar=False) + 1e-6 * np.eye(k_comp)
    inv_cov_g = np.linalg.pinv(cov_g_10)
    inv_cov_t = np.linalg.pinv(cov_t_10)

    # Entropy weights
    var_ed = np.var(np.linalg.norm(sc_g - mu_g_10, axis=1)) + 1e-6
    var_md = np.var([np.sqrt(np.maximum(0, (x - mu_g_10) @ inv_cov_g @ (x - mu_g_10).T)) for x in sc_g]) + 1e-6
    entropy_ed = - (var_ed / (var_ed + var_md)) * np.log2(var_ed / (var_ed + var_md))
    entropy_md = - (var_md / (var_ed + var_md)) * np.log2(var_md / (var_ed + var_md))
    a1 = float(entropy_ed / (entropy_ed + entropy_md))
    a2 = float(entropy_md / (entropy_ed + entropy_md))

    # Evaluate classification for each chip
    pred_labels = []
    r_fd_golden = []
    r_fd_trojan = []

    for i in range(n_samples):
        x_raw = X[i]
        ed_g = np.linalg.norm(x_raw - v_golden)
        ed_t = np.linalg.norm(x_raw - v_trojan)

        x_proj = (x_raw - X_mean) @ coeff
        diff_g = x_proj - mu_g_10
        diff_t = x_proj - mu_t_10
        md_g = np.sqrt(np.maximum(0.0, diff_g @ inv_cov_g @ diff_g.T))
        md_t = np.sqrt(np.maximum(0.0, diff_t @ inv_cov_t @ diff_t.T))

        fd_g = a1 * ed_g + a2 * md_g
        fd_t = a1 * ed_t + a2 * md_t
        r_fd = fd_g / (fd_t + 1e-12)

        pred = 1 if r_fd >= 1.0 else 0
        pred_labels.append(pred)

        if true_labels[i] == 0:
            r_fd_golden.append(r_fd)
        else:
            r_fd_trojan.append(r_fd)

    pred_labels = np.array(pred_labels)
    accuracy = float(np.mean(pred_labels == true_labels) * 100.0)

    fp = int(np.sum((pred_labels == 1) & (true_labels == 0)))
    tn = int(np.sum((pred_labels == 0) & (true_labels == 0)))
    fpr = float(fp / (fp + tn) * 100.0 if (fp + tn) > 0 else 0.0)

    mean_rfd_g = float(np.mean(r_fd_golden)) if len(r_fd_golden) > 0 else 1.0
    mean_rfd_t = float(np.mean(r_fd_trojan)) if len(r_fd_trojan) > 0 else 1.0
    sep_margin = float(mean_rfd_t / (mean_rfd_g + 1e-12))

    return accuracy, fpr, mean_rfd_g, mean_rfd_t, sep_margin

def main():
    print("[+] Executing SPECTRA Script 05: PVT & SNR Sensitivity Sweep...")

    snr_levels = [30, 25, 20, 15, 10, 5]
    drift_levels = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

    # Experiment 1: SNR Sweep (at nominal die drift 0.5%)
    print("[*] Experiment 1: Evaluating SNR Sweep (30 dB -> 5 dB, Drift = 0.5%)...")
    snr_results = {
        "snr_db": snr_levels,
        "method_a_he": {"accuracy": [], "fpr": [], "sep_margin": []},
        "method_b_spectra": {"accuracy": [], "fpr": [], "sep_margin": []}
    }

    for snr in snr_levels:
        xa_list, xb_list, y_list, raw_e_list = [], [], [], []

        # 24 Golden chips
        for i in range(N_CHIPS_GOLDEN):
            drift_die = 0.5 + np.random.normal(0, 0.05)
            t = generate_chip_trace(is_trojan=False, snr_db=snr, clk_drift_pct=drift_die, chip_id=i)
            ea, eb, raw_e = extract_eigenvectors_both_methods(t)
            xa_list.append(ea)
            xb_list.append(eb)
            raw_e_list.append(raw_e)
            y_list.append(0)

        # 24 Trojan chips
        for i in range(N_CHIPS_TROJAN):
            drift_die = 0.5 + np.random.normal(0, 0.05)
            t = generate_chip_trace(is_trojan=True, snr_db=snr, clk_drift_pct=drift_die, chip_id=i + 50)
            ea, eb, raw_e = extract_eigenvectors_both_methods(t)
            xa_list.append(ea)
            xb_list.append(eb)
            raw_e_list.append(raw_e)
            y_list.append(1)

        Xa = np.array(xa_list)
        Xb = np.array(xb_list)
        y = np.array(y_list)
        raw_e = np.array(raw_e_list)

        acc_a, fpr_a, _, _, sep_a = run_fcm_sea_pca_classifier(Xa, y, raw_e)
        acc_b, fpr_b, _, _, sep_b = run_fcm_sea_pca_classifier(Xb, y, raw_e)

        snr_results["method_a_he"]["accuracy"].append(acc_a)
        snr_results["method_a_he"]["fpr"].append(fpr_a)
        snr_results["method_a_he"]["sep_margin"].append(sep_a)

        snr_results["method_b_spectra"]["accuracy"].append(acc_b)
        snr_results["method_b_spectra"]["fpr"].append(fpr_b)
        snr_results["method_b_spectra"]["sep_margin"].append(sep_b)

        print(f"    SNR={snr:2d} dB | He et al. Acc: {acc_a:5.1f}% (FPR {fpr_a:4.1f}%) | SPECTRA Acc: {acc_b:5.1f}% (FPR {fpr_b:4.1f}%)")

    # Experiment 2: Clock Drift Sweep (at representative SNR = 20 dB)
    print("[*] Experiment 2: Evaluating Clock Drift Sweep (0.0% -> 3.0%, SNR = 20 dB)...")
    drift_results = {
        "drift_pct": drift_levels,
        "method_a_he": {"accuracy": [], "sep_ratio_t": [], "sep_ratio_g": [], "sep_margin": []},
        "method_b_spectra": {"accuracy": [], "sep_ratio_t": [], "sep_ratio_g": [], "sep_margin": []}
    }

    for drift in drift_levels:
        xa_list, xb_list, y_list, raw_e_list = [], [], [], []

        for i in range(N_CHIPS_GOLDEN):
            die_var = np.random.normal(0, 0.05)
            t = generate_chip_trace(is_trojan=False, snr_db=20.0, clk_drift_pct=drift + die_var, chip_id=i)
            ea, eb, raw_e = extract_eigenvectors_both_methods(t)
            xa_list.append(ea)
            xb_list.append(eb)
            raw_e_list.append(raw_e)
            y_list.append(0)

        for i in range(N_CHIPS_TROJAN):
            die_var = np.random.normal(0, 0.05)
            t = generate_chip_trace(is_trojan=True, snr_db=20.0, clk_drift_pct=drift + die_var, chip_id=i + 50)
            ea, eb, raw_e = extract_eigenvectors_both_methods(t)
            xa_list.append(ea)
            xb_list.append(eb)
            raw_e_list.append(raw_e)
            y_list.append(1)

        Xa = np.array(xa_list)
        Xb = np.array(xb_list)
        y = np.array(y_list)
        raw_e = np.array(raw_e_list)

        acc_a, fpr_a, mg_a, mt_a, sep_a = run_fcm_sea_pca_classifier(Xa, y, raw_e)
        acc_b, fpr_b, mg_b, mt_b, sep_b = run_fcm_sea_pca_classifier(Xb, y, raw_e)

        drift_results["method_a_he"]["accuracy"].append(acc_a)
        drift_results["method_a_he"]["sep_ratio_t"].append(mt_a)
        drift_results["method_a_he"]["sep_ratio_g"].append(mg_a)
        drift_results["method_a_he"]["sep_margin"].append(sep_a)

        drift_results["method_b_spectra"]["accuracy"].append(acc_b)
        drift_results["method_b_spectra"]["sep_ratio_t"].append(mt_b)
        drift_results["method_b_spectra"]["sep_ratio_g"].append(mg_b)
        drift_results["method_b_spectra"]["sep_margin"].append(sep_b)

        print(f"    Drift={drift:3.1f}% | He et al. Margin: {sep_a:11.2e} (Acc {acc_a:5.1f}%) | SPECTRA Margin: {sep_b:11.2e} (Acc {acc_b:5.1f}%)")

    # Serialize complete results
    full_report = {
        "sweep_configuration": {
            "sampling_frequency_hz": FS,
            "nominal_clock_hz": F_CLK_NOM,
            "sample_points": N_SAMPLES,
            "chips_per_run": TOTAL_CHIPS,
            "ahbe_bandwidth_khz": 1000.0,
            "window_half_width_khz": 500.0
        },
        "snr_sensitivity_sweep": snr_results,
        "clock_drift_sweep": drift_results
    }

    report_path = REPORTS_DIR / "noise_robustness_results.json"
    with open(report_path, "w") as f:
        json.dump(full_report, f, indent=2)
    print(f"[+] Serialized sensitivity results to {report_path}")

    # Generate Dual-Panel Publication Plot (300 DPI)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)

    # Panel 1: Accuracy vs. SNR (dB)
    ax1.plot(snr_levels, snr_results["method_b_spectra"]["accuracy"], 's-', color='#107C41', linewidth=2.4, markersize=8, label='SPECTRA (AHBE Bands)')
    ax1.plot(snr_levels, snr_results["method_a_he"]["accuracy"], 'o--', color='#C0392B', linewidth=2.0, markersize=8, label='Baseline He et al. (Single-Bin)')
    ax1.axhline(100.0, color='#0A192F', linestyle=':', alpha=0.6, linewidth=1.0)
    ax1.set_title("Panel 1: Classification Accuracy vs. SNR (dB)", fontsize=11, fontweight='bold', pad=10)
    ax1.set_xlabel("Signal-to-Noise Ratio (SNR in dB)", fontsize=10, fontweight='bold')
    ax1.set_ylabel("Detection Accuracy (%)", fontsize=10, fontweight='bold')
    ax1.set_ylim(40, 105)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="lower left", frameon=True, fontsize=9)

    # Panel 2: Separation Margin vs. Clock Drift (%)
    ax2.plot(drift_levels, drift_results["method_b_spectra"]["sep_margin"], 's-', color='#0A192F', linewidth=2.4, markersize=8, label='SPECTRA AHBE Margin')
    ax2.plot(drift_levels, drift_results["method_a_he"]["sep_margin"], '^--', color='#D97706', linewidth=2.0, markersize=8, label='Baseline He et al. Margin')
    ax2.set_yscale('log')
    ax2.set_title(r"Panel 2: Dynamic Separation Margin ($R_{FD,T} / R_{FD,G}$) vs. Clock Drift", fontsize=11, fontweight='bold', pad=10)
    ax2.set_xlabel(r"Oscillator Frequency Drift $\Delta f_{\mathrm{clk}}$ (%)", fontsize=10, fontweight='bold')
    ax2.set_ylabel("Separation Margin (Log Scale)", fontsize=10, fontweight='bold')
    ax2.grid(True, linestyle="--", alpha=0.5, which="both")
    ax2.legend(loc="upper right", frameon=True, fontsize=9)

    plt.tight_layout()
    plot_path = SCREENSHOTS_DIR / "noise_robustness_sweep.png"
    plt.savefig(plot_path, dpi=300)
    plt.close()
    print(f"[+] Exported 300 DPI publication figure to {plot_path}")

if __name__ == "__main__":
    main()
