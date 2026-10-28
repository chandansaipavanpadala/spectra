#!/usr/bin/env python3
"""
SPECTRA - Script 05: Process Variation, SNR Sensitivity & Clock Drift Stress Test
Reference Conformance: IEEE JIOT 2024 (Eq. 1 - Eq. 20)
Stress Test: Signal-to-Noise Ratio (30 dB -> 5 dB) & Clock Drift (0.0% -> 3.0%)
Evaluation: Method A (Baseline He et al. 2024) vs. Method B (SPECTRA AHBE)
Standard Conformance: IEEE Std 1364-2001 & PEP 8
"""

import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Repository Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
SCREENSHOTS_DIR = REPO_ROOT / "screenshots"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Fixed Experimental Parameters (IEEE JIOT 2024 Sec. IV-A)
FS = 2.5e9           # Sampling frequency: 2.5 GHz
F_CLK_NOM = 10e6     # Nominal clock frequency: 10 MHz
N_SAMPLES = 1000000  # 1,000,000 points
N_TRAIN_GOLDEN = 24  # 24 Training Golden chips
N_TRAIN_TROJAN = 24  # 24 Training Trojan chips
N_VAL_GOLDEN = 12    # 12 Validation Golden chips
N_VAL_TROJAN = 12    # 12 Validation Trojan chips
PVT_SIGMA = 0.06     # 6% Inter-Die Process Variation

# Frequency grids for 129-D feature vector (Eq. 3)
SUB_HARMONICS = np.linspace(0, F_CLK_NOM, 65)
HARMONICS = np.linspace(F_CLK_NOM + 5e6, 640e6, 64)
TARGET_FREQS = np.concatenate([SUB_HARMONICS, HARMONICS])


def generate_chip_trace(is_trojan=False, snr_db=20.0, clk_drift_pct=0.0,
                        chip_id=0, pvt_sigma=0.06):
    """
    Synthesize 1M-point time-domain power proxy trace d[t] with calibrated
    inter-die process variation (6%), clock drift/phase jitter, and AWGN.

    Args:
        is_trojan (bool): Flag indicating Trojan payload presence.
        snr_db (float): Signal-to-Noise Ratio in decibels.
        clk_drift_pct (float): Clock frequency shift in percent.
        chip_id (int): Deterministic random seed identifier.
        pvt_sigma (float): Inter-die process variation standard deviation (0.06 = 6%).

    Returns:
        np.ndarray: Synthesized 1M-point time-domain trace.
    """
    np.random.seed(chip_id * 37 + (5000 if is_trojan else 100))
    t = np.arange(N_SAMPLES) / FS

    # Actual clock frequency under thermal drift / phase jitter
    f_clk = F_CLK_NOM * (1.0 + clk_drift_pct / 100.0)

    # 6% Inter-die process variation (threshold voltage & capacitive scaling)
    power_scale = 1.0 + np.random.normal(0, pvt_sigma)

    # Core switching clock harmonics (10 MHz fundamental + harmonics)
    core_power = power_scale * (
        0.80 * np.sin(2 * np.pi * f_clk * t) +
        0.40 * np.sin(2 * np.pi * (2 * f_clk) * t) +
        0.20 * np.sin(2 * np.pi * (3 * f_clk) * t) +
        0.10 * np.sin(2 * np.pi * (4 * f_clk) * t)
    )

    # Inter-die low-frequency wander & PVT envelope variation
    pvt_drift = 0.05 * np.sin(2 * np.pi * 50e3 * t) + np.random.normal(0, 0.003, N_SAMPLES)
    signal = core_power + pvt_drift

    # Hardware Trojan localized capacitive switching (inter-harmonics at 1.5, 2.5, 3.5 * f_clk)
    if is_trojan:
        trojan_leakage = (
            0.25 * np.sin(2 * np.pi * (1.5 * f_clk) * t) +
            0.18 * np.cos(2 * np.pi * (2 * f_clk) * t) +
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
      - Method A: Baseline He et al. (single-bin discrete sampling, Eq. 3)
      - Method B: SPECTRA AHBE (continuous band integration +/- 500 kHz)

    Args:
        trace (np.ndarray): 1M-point time-domain power trace.

    Returns:
        tuple: (ev_a, ev_b, raw_energy)
    """
    fft_vals = np.fft.fftshift(np.fft.fft(trace, n=N_SAMPLES))
    pos_spectrum = np.abs(fft_vals[500000:1000000])  # 0 to 1.25 GHz
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


def run_fcm_sea_pca_classifier(X_train, y_train, raw_energies_train, X_val, y_val):
    """
    Executes the downstream SPECTRA classification pipeline:
      1. Unsupervised FCM (c=2, m=2.0) on training set (48 chips)
      2. SEA labeling (int |V_T|^2 > int |V_G|^2)
      3. 10-D PCA subspace projection
      4. Entropy-Weighted Adaptive Distance Fusion (a1 * ED + a2 * MD)
      5. Validation evaluation on 24 unseen validation chips (12 G, 12 T)

    Returns:
        dict: Performance metrics including accuracy, precision, recall, FPR, FNR,
              mean_rfd_g, mean_rfd_t, and dynamic separation margin.
    """
    n_samples, n_features = X_train.shape
    c = 2
    m = 2.0

    # Step 1: FCM Clustering on Training Set
    np.random.seed(42)
    U = np.random.dirichlet(np.ones(c), size=n_samples)

    for _ in range(60):
        U_prev = U.copy()
        Um = U ** m
        V = (Um.T @ X_train) / (np.sum(Um, axis=0)[:, np.newaxis] + 1e-12)

        D_mat = np.zeros((n_samples, c))
        for j in range(c):
            D_mat[:, j] = np.linalg.norm(X_train - V[j], axis=1)
        D_mat = np.maximum(D_mat, 1e-12)

        power_exp = 2.0 / (m - 1.0)
        for j in range(c):
            denom = np.sum((D_mat[:, j:j + 1] / D_mat) ** power_exp, axis=1)
            U[:, j] = 1.0 / (denom + 1e-12)

        if np.max(np.abs(U - U_prev)) < 1e-5:
            break

    # Step 2: Spectral Energy Analysis (SEA) cluster identification (Eq. 13)
    # Energy integral: int |V_T|^2 df > int |V_G|^2 df
    Um = U ** m
    e_c0 = np.sum(Um[:, 0] * raw_energies_train) / np.sum(Um[:, 0])
    e_c1 = np.sum(Um[:, 1] * raw_energies_train) / np.sum(Um[:, 1])

    if e_c0 >= e_c1:
        v_trojan = V[0]
        v_golden = V[1]
    else:
        v_trojan = V[1]
        v_golden = V[0]

    # Step 3: PCA 10-D Subspace Projection
    X_mean = np.mean(X_train, axis=0)
    X_centered = X_train - X_mean
    cov_matrix = np.cov(X_centered, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
    sorted_idx = np.argsort(eigenvalues)[::-1]
    k_comp = min(10, n_samples - 1)
    coeff = eigenvectors[:, sorted_idx[:k_comp]]

    scores_train = X_centered @ coeff
    mu_g_10 = (v_golden - X_mean) @ coeff
    mu_t_10 = (v_trojan - X_mean) @ coeff

    sc_g = scores_train[y_train == 0]
    sc_t = scores_train[y_train == 1]
    cov_g_10 = np.cov(sc_g, rowvar=False) + 1e-6 * np.eye(k_comp)
    cov_t_10 = np.cov(sc_t, rowvar=False) + 1e-6 * np.eye(k_comp)
    inv_cov_g = np.linalg.pinv(cov_g_10)
    inv_cov_t = np.linalg.pinv(cov_t_10)

    # Step 4: Entropy-Weighted Distance Fusion Weights (a1, a2)
    var_ed = np.var(np.linalg.norm(sc_g - mu_g_10, axis=1)) + 1e-6
    var_md = np.var([np.sqrt(np.maximum(0, (x - mu_g_10) @ inv_cov_g @ (x - mu_g_10).T)) for x in sc_g]) + 1e-6
    entropy_ed = - (var_ed / (var_ed + var_md)) * np.log2(var_ed / (var_ed + var_md))
    entropy_md = - (var_md / (var_ed + var_md)) * np.log2(var_md / (var_ed + var_md))
    a1 = float(entropy_ed / (entropy_ed + entropy_md))
    a2 = float(entropy_md / (entropy_ed + entropy_md))

    # Step 5: Evaluate Classification on Unseen Validation Chips
    n_val = len(y_val)
    pred_labels = []
    r_fd_golden = []
    r_fd_trojan = []

    for i in range(n_val):
        x_raw = X_val[i]
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

        if y_val[i] == 0:
            r_fd_golden.append(r_fd)
        else:
            r_fd_trojan.append(r_fd)

    pred_labels = np.array(pred_labels)
    tp = int(np.sum((pred_labels == 1) & (y_val == 1)))
    fp = int(np.sum((pred_labels == 1) & (y_val == 0)))
    tn = int(np.sum((pred_labels == 0) & (y_val == 0)))
    fn = int(np.sum((pred_labels == 0) & (y_val == 1)))

    accuracy = float(np.mean(pred_labels == y_val) * 100.0)
    precision = float(tp / (tp + fp) * 100.0 if (tp + fp) > 0 else 100.0)
    recall = float(tp / (tp + fn) * 100.0 if (tp + fn) > 0 else 100.0)
    fpr = float(fp / (fp + tn) * 100.0 if (fp + tn) > 0 else 0.0)
    fnr = float(fn / (fn + tp) * 100.0 if (fn + tp) > 0 else 0.0)

    mean_rfd_g = float(np.mean(r_fd_golden)) if len(r_fd_golden) > 0 else 1.0
    mean_rfd_t = float(np.mean(r_fd_trojan)) if len(r_fd_trojan) > 0 else 1.0
    sep_margin = float(mean_rfd_t / (mean_rfd_g + 1e-12))

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "fpr": fpr,
        "fnr": fnr,
        "mean_rfd_g": mean_rfd_g,
        "mean_rfd_t": mean_rfd_t,
        "sep_margin": sep_margin,
        "confusion_matrix": {"TP": tp, "FP": fp, "TN": tn, "FN": fn}
    }


def main():
    print("[+] Executing SPECTRA Script 05: PVT, SNR & Clock Drift Stress Test...")

    snr_levels = [30, 25, 20, 15, 10, 5]
    drift_levels = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

    # --------------------------------------------------------------------------
    # Experiment 1: SNR Sensitivity Sweep (30 dB -> 5 dB, Drift = 0.5%)
    # --------------------------------------------------------------------------
    print("[*] Experiment 1: Evaluating SNR Sweep (30 dB -> 5 dB, Drift = 0.5%, PVT = 6%)...")
    snr_results = {
        "snr_db": snr_levels,
        "method_a_he": {"accuracy": [], "fpr": [], "fnr": [], "sep_margin": []},
        "method_b_spectra": {"accuracy": [], "fpr": [], "fnr": [], "sep_margin": []}
    }

    for snr in snr_levels:
        xa_tr, xb_tr, y_tr, raw_e_tr = [], [], [], []
        xa_val, xb_val, y_val = [], [], []

        # 24 Training Golden chips
        for i in range(N_TRAIN_GOLDEN):
            drift_die = 0.5 + np.random.normal(0, 0.02)
            t = generate_chip_trace(is_trojan=False, snr_db=snr, clk_drift_pct=drift_die,
                                    chip_id=i, pvt_sigma=PVT_SIGMA)
            ea, eb, raw_e = extract_eigenvectors_both_methods(t)
            xa_tr.append(ea)
            xb_tr.append(eb)
            raw_e_tr.append(raw_e)
            y_tr.append(0)

        # 24 Training Trojan chips
        for i in range(N_TRAIN_TROJAN):
            drift_die = 0.5 + np.random.normal(0, 0.02)
            t = generate_chip_trace(is_trojan=True, snr_db=snr, clk_drift_pct=drift_die,
                                    chip_id=i + 50, pvt_sigma=PVT_SIGMA)
            ea, eb, raw_e = extract_eigenvectors_both_methods(t)
            xa_tr.append(ea)
            xb_tr.append(eb)
            raw_e_tr.append(raw_e)
            y_tr.append(1)

        # 12 Validation Golden chips
        for i in range(N_VAL_GOLDEN):
            drift_die = 0.5 + np.random.normal(0, 0.02)
            t = generate_chip_trace(is_trojan=False, snr_db=snr, clk_drift_pct=drift_die,
                                    chip_id=i + 200, pvt_sigma=PVT_SIGMA)
            ea, eb, _ = extract_eigenvectors_both_methods(t)
            xa_val.append(ea)
            xb_val.append(eb)
            y_val.append(0)

        # 12 Validation Trojan chips
        for i in range(N_VAL_TROJAN):
            drift_die = 0.5 + np.random.normal(0, 0.02)
            t = generate_chip_trace(is_trojan=True, snr_db=snr, clk_drift_pct=drift_die,
                                    chip_id=i + 250, pvt_sigma=PVT_SIGMA)
            ea, eb, _ = extract_eigenvectors_both_methods(t)
            xa_val.append(ea)
            xb_val.append(eb)
            y_val.append(1)

        Xa_tr, Xb_tr = np.array(xa_tr), np.array(xb_tr)
        y_tr, raw_e_tr = np.array(y_tr), np.array(raw_e_tr)
        Xa_val, Xb_val = np.array(xa_val), np.array(xb_val)
        y_val = np.array(y_val)

        res_a = run_fcm_sea_pca_classifier(Xa_tr, y_tr, raw_e_tr, Xa_val, y_val)
        res_b = run_fcm_sea_pca_classifier(Xb_tr, y_tr, raw_e_tr, Xb_val, y_val)

        snr_results["method_a_he"]["accuracy"].append(res_a["accuracy"])
        snr_results["method_a_he"]["fpr"].append(res_a["fpr"])
        snr_results["method_a_he"]["fnr"].append(res_a["fnr"])
        snr_results["method_a_he"]["sep_margin"].append(res_a["sep_margin"])

        snr_results["method_b_spectra"]["accuracy"].append(res_b["accuracy"])
        snr_results["method_b_spectra"]["fpr"].append(res_b["fpr"])
        snr_results["method_b_spectra"]["fnr"].append(res_b["fnr"])
        snr_results["method_b_spectra"]["sep_margin"].append(res_b["sep_margin"])

        print(f"    SNR={snr:2d} dB | He: Acc {res_a['accuracy']:5.1f}% (FPR {res_a['fpr']:4.1f}%, FNR {res_a['fnr']:4.1f}%) "
              f"| SPECTRA: Acc {res_b['accuracy']:5.1f}% (FPR {res_b['fpr']:4.1f}%, FNR {res_b['fnr']:4.1f}%, Margin {res_b['sep_margin']:.2e})")

    # --------------------------------------------------------------------------
    # Experiment 2: Clock Drift Sweep (0.0% -> 3.0%, SNR = 20 dB)
    # --------------------------------------------------------------------------
    print("[*] Experiment 2: Evaluating Clock Drift Sweep (0.0% -> 3.0%, SNR = 20 dB, PVT = 6%)...")
    drift_results = {
        "drift_pct": drift_levels,
        "method_a_he": {"accuracy": [], "fpr": [], "fnr": [], "sep_ratio_t": [], "sep_ratio_g": [], "sep_margin": []},
        "method_b_spectra": {"accuracy": [], "fpr": [], "fnr": [], "sep_ratio_t": [], "sep_ratio_g": [], "sep_margin": []}
    }

    for drift in drift_levels:
        xa_tr, xb_tr, y_tr, raw_e_tr = [], [], [], []
        xa_val, xb_val, y_val = [], [], []

        for i in range(N_TRAIN_GOLDEN):
            die_var = np.random.normal(0, 0.02)
            t = generate_chip_trace(is_trojan=False, snr_db=20.0, clk_drift_pct=drift + die_var,
                                    chip_id=i, pvt_sigma=PVT_SIGMA)
            ea, eb, raw_e = extract_eigenvectors_both_methods(t)
            xa_tr.append(ea)
            xb_tr.append(eb)
            raw_e_tr.append(raw_e)
            y_tr.append(0)

        for i in range(N_TRAIN_TROJAN):
            die_var = np.random.normal(0, 0.02)
            t = generate_chip_trace(is_trojan=True, snr_db=20.0, clk_drift_pct=drift + die_var,
                                    chip_id=i + 50, pvt_sigma=PVT_SIGMA)
            ea, eb, raw_e = extract_eigenvectors_both_methods(t)
            xa_tr.append(ea)
            xb_tr.append(eb)
            raw_e_tr.append(raw_e)
            y_tr.append(1)

        for i in range(N_VAL_GOLDEN):
            die_var = np.random.normal(0, 0.02)
            t = generate_chip_trace(is_trojan=False, snr_db=20.0, clk_drift_pct=drift + die_var,
                                    chip_id=i + 200, pvt_sigma=PVT_SIGMA)
            ea, eb, _ = extract_eigenvectors_both_methods(t)
            xa_val.append(ea)
            xb_val.append(eb)
            y_val.append(0)

        for i in range(N_VAL_TROJAN):
            die_var = np.random.normal(0, 0.02)
            t = generate_chip_trace(is_trojan=True, snr_db=20.0, clk_drift_pct=drift + die_var,
                                    chip_id=i + 250, pvt_sigma=PVT_SIGMA)
            ea, eb, _ = extract_eigenvectors_both_methods(t)
            xa_val.append(ea)
            xb_val.append(eb)
            y_val.append(1)

        Xa_tr, Xb_tr = np.array(xa_tr), np.array(xb_tr)
        y_tr, raw_e_tr = np.array(y_tr), np.array(raw_e_tr)
        Xa_val, Xb_val = np.array(xa_val), np.array(xb_val)
        y_val = np.array(y_val)

        res_a = run_fcm_sea_pca_classifier(Xa_tr, y_tr, raw_e_tr, Xa_val, y_val)
        res_b = run_fcm_sea_pca_classifier(Xb_tr, y_tr, raw_e_tr, Xb_val, y_val)

        drift_results["method_a_he"]["accuracy"].append(res_a["accuracy"])
        drift_results["method_a_he"]["fpr"].append(res_a["fpr"])
        drift_results["method_a_he"]["fnr"].append(res_a["fnr"])
        drift_results["method_a_he"]["sep_ratio_t"].append(res_a["mean_rfd_t"])
        drift_results["method_a_he"]["sep_ratio_g"].append(res_a["mean_rfd_g"])
        drift_results["method_a_he"]["sep_margin"].append(res_a["sep_margin"])

        drift_results["method_b_spectra"]["accuracy"].append(res_b["accuracy"])
        drift_results["method_b_spectra"]["fpr"].append(res_b["fpr"])
        drift_results["method_b_spectra"]["fnr"].append(res_b["fnr"])
        drift_results["method_b_spectra"]["sep_ratio_t"].append(res_b["mean_rfd_t"])
        drift_results["method_b_spectra"]["sep_ratio_g"].append(res_b["mean_rfd_g"])
        drift_results["method_b_spectra"]["sep_margin"].append(res_b["sep_margin"])

        print(f"    Drift={drift:3.1f}% | He: Margin {res_a['sep_margin']:9.2e} (Acc {res_a['accuracy']:5.1f}%) "
              f"| SPECTRA: Margin {res_b['sep_margin']:9.2e} (Acc {res_b['accuracy']:5.1f}%)")

    # Serialize complete results
    full_report = {
        "sweep_configuration": {
            "sampling_frequency_hz": FS,
            "nominal_clock_hz": F_CLK_NOM,
            "sample_points": N_SAMPLES,
            "training_chips": N_TRAIN_GOLDEN + N_TRAIN_TROJAN,
            "validation_chips": N_VAL_GOLDEN + N_VAL_TROJAN,
            "pvt_process_variation_sigma": PVT_SIGMA,
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
    ax1.plot(snr_levels, snr_results["method_b_spectra"]["accuracy"], 's-', color='#107C41',
             linewidth=2.4, markersize=8, label='SPECTRA (AHBE Bands)')
    ax1.plot(snr_levels, snr_results["method_a_he"]["accuracy"], 'o--', color='#C0392B',
             linewidth=2.0, markersize=8, label='Baseline He et al. (Single-Bin)')
    ax1.axhline(100.0, color='#0A192F', linestyle=':', alpha=0.6, linewidth=1.0)
    ax1.set_title("Panel 1: Classification Accuracy vs. SNR (dB)", fontsize=11, fontweight='bold', pad=10)
    ax1.set_xlabel("Signal-to-Noise Ratio (SNR in dB)", fontsize=10, fontweight='bold')
    ax1.set_ylabel("Detection Accuracy (%)", fontsize=10, fontweight='bold')
    ax1.set_ylim(40, 105)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="lower left", frameon=True, fontsize=9)

    # Panel 2: Separation Margin vs. Clock Drift (%)
    ax2.plot(drift_levels, drift_results["method_b_spectra"]["sep_margin"], 's-', color='#0A192F',
             linewidth=2.4, markersize=8, label=r'SPECTRA AHBE ($R_{FD,T} / R_{FD,G}$)')
    ax2.plot(drift_levels, drift_results["method_a_he"]["sep_margin"], '^--', color='#D97706',
             linewidth=2.0, markersize=8, label=r'Baseline He et al. ($R_{FD,T} / R_{FD,G}$)')
    ax2.set_yscale('log')
    ax2.set_title(r"Panel 2: Dynamic Separation Ratio ($R_{FD}$) vs. Clock Frequency Drift ($\pm \%$)",
                  fontsize=11, fontweight='bold', pad=10)
    ax2.set_xlabel(r"Clock Frequency Drift $\Delta f_{\mathrm{clk}}$ ($\pm \%$)", fontsize=10, fontweight='bold')
    ax2.set_ylabel("Dynamic Separation Ratio (Log Scale)", fontsize=10, fontweight='bold')
    ax2.grid(True, linestyle="--", alpha=0.5, which="both")
    ax2.legend(loc="upper right", frameon=True, fontsize=9)

    plt.tight_layout()
    plot_path = SCREENSHOTS_DIR / "noise_robustness_sweep.png"
    plt.savefig(plot_path, dpi=300)
    plt.close()
    print(f"[+] Exported 300 DPI publication figure to {plot_path}")


if __name__ == "__main__":
    main()
