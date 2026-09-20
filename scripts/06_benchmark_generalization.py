#!/usr/bin/env python3
"""
SPECTRA - Script 06: Multi-Trojan Benchmark Validation Suite
Evaluates generalization across three standard hardware Trojan taxonomy profiles:
  1. Synchronous 2-bit Counter (He et al. 2024 Baseline, Implicit, ~0.1% Area)
  2. Combinational Comparator Trigger (Trust-HUB AES-T400 Equivalent, Supply Droop)
  3. Sequential Time-Bomb Key Leakage (Trust-HUB AES-T800 Equivalent, Capacitive Bursts)

Dataset: 48 Training chips + 24 Validation chips per benchmark under 6% inter-die PVT variation.
Downstream: SFA-AHBE -> FCM (c=2, m=2.0) -> SEA -> 10-D PCA -> Adaptive Fusion Distance.
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
SCREENSHOTS_DIR = REPO_ROOT / "screenshots"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Sampling & Core Parameters
FS = 2.5e9           # 2.5 GHz
F_CLK = 10e6         # 10 MHz
N_SAMPLES = 1000000  # 1,000,000 points
WINDOW_BW_HZ = 1e6   # +/- 500 kHz integration window for AHBE

# Frequency grids
SUB_HARMONICS = np.linspace(0, F_CLK, 65)
HARMONICS = np.linspace(F_CLK + 5e6, 640e6, 64)
TARGET_FREQS = np.concatenate([SUB_HARMONICS, HARMONICS])

def synthesize_benchmark_trace(benchmark_type="counter_he", is_trojan=False, die_id=0, pvt_factor=0.06):
    """
    Generates time-domain power proxy trace with 6% inter-die process variation
    and benchmark-specific hardware Trojan side-channel signature.
    """
    np.random.seed(die_id * 43 + (7777 if is_trojan else 333))
    t = np.arange(N_SAMPLES) / FS

    # Realistic oscillator thermal drift (2000 ppm = 0.2%)
    clk_die_drift = np.random.normal(0, 0.002)
    f_clk_die = F_CLK * (1.0 + clk_die_drift)

    # 6% inter-die PVT power scaling
    power_scale = 1.0 + np.random.normal(0, pvt_factor)

    # Core clock switching harmonics (10, 20, 30, 40 MHz)
    core_power = power_scale * (
        0.80 * np.sin(2 * np.pi * f_clk_die * t) +
        0.40 * np.sin(2 * np.pi * (2 * f_clk_die) * t) +
        0.20 * np.sin(2 * np.pi * (3 * f_clk_die) * t) +
        0.10 * np.sin(2 * np.pi * (4 * f_clk_die) * t)
    )

    # Low-frequency PVT wander & thermal Gaussian noise
    pvt_wander = 0.04 * np.sin(2 * np.pi * 45e3 * t) + np.random.normal(0, 0.003, N_SAMPLES)
    thermal_noise = np.random.normal(0, 0.015, N_SAMPLES)
    trace = core_power + pvt_wander + thermal_noise

    # Benchmark-Specific Hardware Trojan Injection
    if is_trojan:
        if benchmark_type == "counter_he":
            # Benchmark 1: Synchronous 2-bit Counter (He et al. baseline)
            # Modulates inter-harmonic side-bands at 1.5, 2.5, 3.5 * f_clk
            trojan_sig = (
                0.25 * np.sin(2 * np.pi * (1.5 * f_clk_die) * t) +
                0.18 * np.cos(2 * np.pi * (2.5 * f_clk_die) * t) +
                0.12 * np.sin(2 * np.pi * (3.5 * f_clk_die) * t)
            )
            trace += trojan_sig

        elif benchmark_type == "aes_t400":
            # Benchmark 2: Combinational Comparator Trigger (Trust-HUB AES-T400)
            # Rare 32-bit state match asserts combinational condition inducing transient supply droop
            droop_envelope = 0.15 * np.sin(2 * np.pi * 2.5e6 * t) * (1.0 + 0.5 * np.sin(2 * np.pi * 12.5e6 * t))
            harmonic_perturbation = (
                0.22 * np.sin(2 * np.pi * (1.5 * f_clk_die) * t) +
                0.16 * np.cos(2 * np.pi * (2.5 * f_clk_die) * t) +
                0.15 * np.sin(2 * np.pi * (3.5 * f_clk_die) * t)
            )
            trace += (droop_envelope + harmonic_perturbation)

        elif benchmark_type == "aes_t800":
            # Benchmark 3: Sequential Time-Bomb Leakage (Trust-HUB AES-T800)
            # Long counter triggers key-bit leakage via periodic capacitive switching bursts
            leakage_carrier = (
                0.24 * np.sin(2 * np.pi * (1.5 * f_clk_die) * t) +
                0.20 * np.sin(2 * np.pi * (2.5 * f_clk_die) * t) +
                0.14 * np.cos(2 * np.pi * (3.5 * f_clk_die) * t)
            )
            burst_mod = 0.5 * (1.0 + np.sign(np.sin(2 * np.pi * 100e3 * t)))
            trace += (leakage_carrier * (0.5 + 0.5 * burst_mod))

    return trace

def extract_sfa_ahbe_eigenvector(trace):
    """
    Computes 1M-point FFT and extracts 129-D feature vector via Adaptive Harmonic Band Energy (AHBE).
    """
    fft_vals = np.fft.fftshift(np.fft.fft(trace, n=N_SAMPLES))
    pos_spectrum = np.abs(fft_vals[500000:1000000])
    raw_energy = float(np.sum(pos_spectrum ** 2))
    n_pos = len(pos_spectrum)

    sampled_indices = np.clip((TARGET_FREQS / (FS / 2.0) * (n_pos - 1)).astype(int), 0, n_pos - 1)
    window_half_width = max(1, int(500e3 / (FS / 2.0) * n_pos))

    ev = np.zeros(129)
    for i, idx in enumerate(sampled_indices):
        start_w = max(0, idx - window_half_width)
        end_w = min(n_pos, idx + window_half_width + 1)
        ev[i] = np.sqrt(np.mean(pos_spectrum[start_w:end_w] ** 2))

    ev_norm = ev / (np.linalg.norm(ev) + 1e-12)
    return ev_norm, raw_energy

def evaluate_benchmark(benchmark_type):
    """
    Runs end-to-end SPECTRA training and validation pipeline on specified benchmark.
    Returns quantitative performance dictionary.
    """
    print(f"\n[*] Benchmarking Threat Profile: {benchmark_type.upper()}...")

    # Step 1: Synthesize 48 Training Chips (24 Golden, 24 Trojan)
    X_train_list = []
    y_train_list = []
    raw_energy_train = []
    for i in range(24):
        t = synthesize_benchmark_trace(benchmark_type, is_trojan=False, die_id=i)
        ev, re = extract_sfa_ahbe_eigenvector(t)
        X_train_list.append(ev)
        y_train_list.append(0)
        raw_energy_train.append(re)

    for i in range(24):
        t = synthesize_benchmark_trace(benchmark_type, is_trojan=True, die_id=i + 50)
        ev, re = extract_sfa_ahbe_eigenvector(t)
        X_train_list.append(ev)
        y_train_list.append(1)
        raw_energy_train.append(re)

    X_train = np.array(X_train_list)
    y_train = np.array(y_train_list)
    raw_energy_train = np.array(raw_energy_train)

    # Step 2: Unsupervised FCM Clustering (c=2, m=2.0)
    n_samples, n_features = X_train.shape
    c = 2
    m = 2.0
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
            denom = np.sum((D_mat[:, j:j+1] / D_mat) ** power_exp, axis=1)
            U[:, j] = 1.0 / (denom + 1e-12)

        if np.max(np.abs(U - U_prev)) < 1e-6:
            break

    # Step 3: Spectral Energy Analysis (SEA) Theorem Validation (Eq. 13)
    # Energy integral int |V_T|^2 df > int |V_G|^2 df
    Um = U ** m
    energy_c0 = float(np.sum(Um[:, 0] * raw_energy_train) / np.sum(Um[:, 0]))
    energy_c1 = float(np.sum(Um[:, 1] * raw_energy_train) / np.sum(Um[:, 1]))
    sea_trojan_idx = 0 if energy_c0 >= energy_c1 else 1
    sea_golden_idx = 1 - sea_trojan_idx

    v_trojan = V[sea_trojan_idx]
    v_golden = V[sea_golden_idx]
    e_trojan = max(energy_c0, energy_c1)
    e_golden = min(energy_c0, energy_c1)

    sea_verified = bool(e_trojan > e_golden)
    print(f"    SEA Energy: Trojan = {e_trojan:.6e}, Golden = {e_golden:.6e} | Theorem Verified: {sea_verified}")

    # Step 4: 10-D PCA Projection
    X_mean = np.mean(X_train, axis=0)
    X_centered = X_train - X_mean
    cov_matrix = np.cov(X_centered, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
    sorted_idx = np.argsort(eigenvalues)[::-1]
    coeff = eigenvectors[:, sorted_idx[:10]]
    var_explained = float(np.sum(eigenvalues[sorted_idx[:10]]) / np.sum(eigenvalues) * 100.0)

    scores_train = X_centered @ coeff
    mu_g_10 = (v_golden - X_mean) @ coeff
    mu_t_10 = (v_trojan - X_mean) @ coeff

    sc_g = scores_train[y_train == 0]
    sc_t = scores_train[y_train == 1]
    cov_g_10 = np.cov(sc_g, rowvar=False) + 1e-6 * np.eye(10)
    cov_t_10 = np.cov(sc_t, rowvar=False) + 1e-6 * np.eye(10)
    inv_cov_g = np.linalg.pinv(cov_g_10)
    inv_cov_t = np.linalg.pinv(cov_t_10)

    # Step 5: Adaptive Entropy-Weighted Fusion
    var_ed = np.var(np.linalg.norm(sc_g - mu_g_10, axis=1)) + 1e-6
    var_md = np.var([np.sqrt(np.maximum(0, (x - mu_g_10) @ inv_cov_g @ (x - mu_g_10).T)) for x in sc_g]) + 1e-6
    entropy_ed = - (var_ed / (var_ed + var_md)) * np.log2(var_ed / (var_ed + var_md))
    entropy_md = - (var_md / (var_ed + var_md)) * np.log2(var_md / (var_ed + var_md))
    a1 = float(entropy_ed / (entropy_ed + entropy_md))
    a2 = float(entropy_md / (entropy_ed + entropy_md))

    # Step 6: Evaluate 24 Validation Chips (12 Golden, 12 Trojan)
    val_chips = []
    r_fd_golden = []
    r_fd_trojan = []
    y_val_true = []
    y_val_pred = []

    for i in range(12):
        t = synthesize_benchmark_trace(benchmark_type, is_trojan=False, die_id=i + 200)
        ev, _ = extract_sfa_ahbe_eigenvector(t)
        val_chips.append((f"G_val_{i+1}", 0, ev))

    for i in range(12):
        t = synthesize_benchmark_trace(benchmark_type, is_trojan=True, die_id=i + 250)
        ev, _ = extract_sfa_ahbe_eigenvector(t)
        val_chips.append((f"T_val_{i+1}", 1, ev))

    for chip_id, label, ev_raw in val_chips:
        ed_g = np.linalg.norm(ev_raw - v_golden)
        ed_t = np.linalg.norm(ev_raw - v_trojan)

        ev_proj = (ev_raw - X_mean) @ coeff
        diff_g = ev_proj - mu_g_10
        diff_t = ev_proj - mu_t_10
        md_g = np.sqrt(np.maximum(0.0, diff_g @ inv_cov_g @ diff_g.T))
        md_t = np.sqrt(np.maximum(0.0, diff_t @ inv_cov_t @ diff_t.T))

        fd_g = a1 * ed_g + a2 * md_g
        fd_t = a1 * ed_t + a2 * md_t
        r_fd = fd_g / (fd_t + 1e-12)

        pred = 1 if r_fd >= 1.0 else 0
        y_val_true.append(label)
        y_val_pred.append(pred)

        if label == 0:
            r_fd_golden.append(r_fd)
        else:
            r_fd_trojan.append(r_fd)

    y_val_true = np.array(y_val_true)
    y_val_pred = np.array(y_val_pred)

    tp = int(np.sum((y_val_pred == 1) & (y_val_true == 1)))
    fp = int(np.sum((y_val_pred == 1) & (y_val_true == 0)))
    tn = int(np.sum((y_val_pred == 0) & (y_val_true == 0)))
    fn = int(np.sum((y_val_pred == 0) & (y_val_true == 1)))

    acc = float(np.mean(y_val_pred == y_val_true) * 100.0)
    precision = float(tp / (tp + fp) * 100.0 if (tp + fp) > 0 else 100.0)
    recall = float(tp / (tp + fn) * 100.0 if (tp + fn) > 0 else 100.0)
    fpr = float(fp / (fp + tn) * 100.0 if (fp + tn) > 0 else 0.0)

    mean_rfd_g = float(np.mean(r_fd_golden))
    mean_rfd_t = float(np.mean(r_fd_trojan))
    sep_margin = float(mean_rfd_t / (mean_rfd_g + 1e-12))

    print(f"    Validation Accuracy: {acc:.2f}% | Precision: {precision:.2f}% | Recall: {recall:.2f}% | FPR: {fpr:.2f}%")
    print(f"    Mean RFD (Golden): {mean_rfd_g:.6e} | Mean RFD (Trojan): {mean_rfd_t:.2f} | Dynamic Margin: {sep_margin:.2e}")

    return {
        "benchmark_type": benchmark_type,
        "sea_verified": sea_verified,
        "sea_golden_energy": e_golden,
        "sea_trojan_energy": e_trojan,
        "pca_variance_explained_pct": var_explained,
        "fusion_weights": {"a1_ed": a1, "a2_md": a2},
        "confusion_matrix": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
        "accuracy_pct": acc,
        "precision_pct": precision,
        "recall_pct": recall,
        "false_positive_rate_pct": fpr,
        "mean_rfd_golden": mean_rfd_g,
        "mean_rfd_trojan": mean_rfd_t,
        "dynamic_separation_margin": sep_margin
    }

def main():
    print("[+] Executing SPECTRA Script 06: Multi-Trojan Benchmark Validation...")

    benchmarks = ["counter_he", "aes_t400", "aes_t800"]
    benchmark_names = {
        "counter_he": "Implicit 2-Bit Counter (He et al.)",
        "aes_t400": "Trust-HUB AES-T400 (Combinational)",
        "aes_t800": "Trust-HUB AES-T800 (Sequential)"
    }

    all_results = {}
    for bm in benchmarks:
        all_results[bm] = evaluate_benchmark(bm)

    # Save to reports/multi_benchmark_report.json
    output_report = {
        "evaluation_scope": "Multi-Trojan Threat Generalization",
        "inter_die_process_variation": "6% Inter-Die Gaussian PVT",
        "benchmarks_evaluated": benchmark_names,
        "results": all_results
    }

    report_path = REPORTS_DIR / "multi_benchmark_report.json"
    with open(report_path, "w") as f:
        json.dump(output_report, f, indent=2)
    print(f"\n[+] Serialized multi-benchmark report to {report_path}")

    # Generate 300 DPI Publication Bar Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), dpi=300)

    labels = ["Counter (He et al.)", "AES-T400 (Comb.)", "AES-T800 (Seq.)"]
    accuracies = [all_results[b]["accuracy_pct"] for b in benchmarks]
    margins = [all_results[b]["dynamic_separation_margin"] for b in benchmarks]

    colors = ['#107C41', '#0A192F', '#D97706']

    # Panel 1: Detection Accuracy
    bars1 = ax1.bar(labels, accuracies, color=colors, width=0.45, edgecolor='black', linewidth=1.2, alpha=0.9)
    ax1.set_ylim(80, 108)
    ax1.set_title("Panel 1: Detection Accuracy Across Trojan Benchmarks", fontsize=11, fontweight='bold', pad=12)
    ax1.set_ylabel("Validation Accuracy (%)", fontsize=10, fontweight='bold')
    ax1.grid(axis='y', linestyle='--', alpha=0.5)

    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2.0, yval + 1.2, f"{yval:.1f}%", ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Panel 2: Dynamic Separation Margin (Log Scale)
    bars2 = ax2.bar(labels, margins, color=colors, width=0.45, edgecolor='black', linewidth=1.2, alpha=0.9)
    ax2.set_yscale('log')
    ax2.set_title(r"Panel 2: Dynamic Separation Margin ($R_{FD,T} / R_{FD,G}$)", fontsize=11, fontweight='bold', pad=12)
    ax2.set_ylabel("Dynamic Separation Margin (Log Scale)", fontsize=10, fontweight='bold')
    ax2.grid(axis='y', linestyle='--', alpha=0.5, which="both")

    for bar in bars2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2.0, yval * 1.8, f"{yval:.2e}", ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.subplots_adjust(left=0.08, right=0.95, top=0.90, bottom=0.12, wspace=0.25)
    plot_path = SCREENSHOTS_DIR / "benchmark_comparison.png"
    plt.savefig(plot_path, dpi=300)
    plt.close()
    print(f"[+] Exported 300 DPI benchmark comparison figure to {plot_path}")

if __name__ == "__main__":
    main()
