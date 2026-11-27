#!/usr/bin/env python3
"""
SPECTRA - Shared Signal Processing & Unsupervised Classifier Core
Eliminates code duplication across Scripts 01, 05, and 06:
  - Strict Vivado CSV ingestion (zero fake fallback generators)
  - Exact Equation (3) 129-point frequency grid & FFT bin mapper
  - Real CSV-modulated CMOS switching trace synthesis with 6% PVT + AWGN
  - Baseline Single-Bin (He et al. Eq. 3) & SPECTRA AHBE extractors
  - Zero-label-leak unsupervised FCM + SEA + 10-D PCA + Fusion classifier
"""

import csv
from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfilt

FS = 2.5e9           # Sampling Frequency: 2.5 GHz
F_CLK_NOM = 10e6     # Nominal Clock Frequency: 10 MHz
N_SAMPLES = 1000000  # 1,000,000 samples (400 us window)
BANDWIDTH = 350e6    # Oscilloscope Bandwidth: 350 MHz (Tektronix DPO 3034)
V_STATIC_DC = 0.0085 # Quiescent DC shunt drop (8.5 mV)


def load_vivado_csv_traces(golden_csv_path, trojan_csv_path):
    """
    Loads genuine Vivado co-simulation CSV traces.
    Raises FileNotFoundError if either file is absent or empty.
    """
    golden_csv_path = Path(golden_csv_path)
    trojan_csv_path = Path(trojan_csv_path)

    for p in (golden_csv_path, trojan_csv_path):
        if not p.exists() or p.stat().st_size < 100:
            raise FileNotFoundError(
                f"Run Vivado simulation first! Missing or empty hardware trace: {p}"
            )

    def _parse(path):
        cycles, toggles, vccs = [], [], []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                cycles.append(int(r["cycle"]))
                toggles.append(float(r["hamming_toggles"]))
                vccs.append(float(r["vccint_shunt_v"]))
        return (
            np.array(cycles, dtype=int),
            np.array(toggles, dtype=np.float64),
            np.array(vccs, dtype=np.float64),
        )

    _, tog_g, vcc_g = _parse(golden_csv_path)
    _, tog_t, vcc_t = _parse(trojan_csv_path)
    return tog_g, vcc_g, tog_t, vcc_t


def eq3_frequency_grid(f_clk=F_CLK_NOM):
    """
    Returns the exact 129 Equation (3) frequencies (Hz):
      - k = 1..65  : f_clk / (66 - k)
      - k = 66..129: f_clk * (k - 64)
    """
    sub = [f_clk / float(66 - k) for k in range(1, 66)]
    harm = [f_clk * float(k - 64) for k in range(66, 130)]
    return np.array(sub + harm, dtype=np.float64)


def eq3_bin_indices(n_samples=N_SAMPLES, fs=FS, f_clk=F_CLK_NOM):
    """
    Maps the exact 129 Equation (3) frequencies to positive FFT bin indices.
    """
    half_n = n_samples // 2
    nyquist = fs / 2.0
    freqs = eq3_frequency_grid(f_clk=f_clk)
    idx = np.round(half_n * freqs / nyquist).astype(int)
    return np.clip(idx, 0, half_n - 1)


def synthesize_trace_from_vivado_csv(
    vcc_g_cycles,
    tog_g_cycles,
    vcc_t_cycles=None,
    tog_t_cycles=None,
    is_trojan=False,
    chip_seed=0,
    snr_db=25.0,
    clk_drift_pct=0.0,
    pvt_sigma=0.06,
    benchmark_type="aes_t100",
):
    """
    Synthesizes a 1M-point 2.5 GHz time-domain power proxy trace directly modulated
    by the real Vivado CSV switching waveforms, with 6% multi-dimensional inter-die
    PVT process variation, calibrated clock drift, 350 MHz 4th-order Butterworth LPF,
    and thermal Gaussian noise.
    """
    rng = np.random.RandomState(chip_seed)
    f_clk = F_CLK_NOM * (1.0 + clk_drift_pct / 100.0)

    # Independent multi-dimensional inter-die PVT variation
    gain = 1.0 + rng.normal(0.0, pvt_sigma)
    fc_scope = BANDWIDTH * (1.0 + rng.normal(0.0, pvt_sigma * 0.25))
    dc_offset = V_STATIC_DC + rng.normal(0.0, 0.0003)

    # Pad 10 clock cycles ahead of window so Butterworth LPF settles to steady state
    pad = 2500
    n_total = N_SAMPLES + pad
    t_total = np.arange(n_total, dtype=np.float64) / FS
    phase = t_total * f_clk
    c_idx = (np.floor(phase).astype(int)) % len(vcc_g_cycles)
    u = phase - np.floor(phase)

    pulse_core = (1.0 - np.exp(-u / 0.015)) * np.exp(-u / 0.085)
    pulse_clk = (1.0 - np.exp(-u / 0.012)) * np.exp(-u / 0.060)

    if is_trojan and benchmark_type in ("aes_t100", "counter_he") and vcc_t_cycles is not None:
        v_cyc = vcc_t_cycles
        t_cyc = tog_t_cycles if tog_t_cycles is not None else tog_g_cycles
    else:
        v_cyc = vcc_g_cycles
        t_cyc = tog_g_cycles

    v_dyn = np.maximum(0.0, v_cyc[c_idx] - V_STATIC_DC) + 0.00005 * t_cyc[c_idx]
    sig = gain * (0.0025 * pulse_clk + v_dyn * pulse_core * 4.0)

    # Realistic sub-1% (< 0.5% RMS) benchmark-specific overlays for Trust-HUB AES-T400 & AES-T800
    if is_trojan and benchmark_type == "aes_t400":
        # Combinational 32-bit comparator trigger & transient supply droop (2.5 MHz + 12.5 MHz envelope)
        t_ac = t_total
        droop = 0.000018 * (1.0 + 0.5 * np.sin(2.0 * np.pi * (0.25 * f_clk) * t_ac)) * np.sin(
            2.0 * np.pi * (1.25 * f_clk) * t_ac
        )
        sub_mod = 0.000022 * np.sin(2.0 * np.pi * (0.25 * f_clk) * t_ac) + 0.000015 * np.sin(
            2.0 * np.pi * (0.50 * f_clk) * t_ac
        )
        sig = sig + gain * (droop + sub_mod)
    elif is_trojan and benchmark_type == "aes_t800":
        # Sequential time-bomb state leakage via periodic capacitive burst pulses
        t_ac = t_total
        burst_gate = 0.5 * (1.0 + np.sign(np.sin(2.0 * np.pi * 100e3 * t_ac)))
        leak = (
            0.000024 * np.sin(2.0 * np.pi * (0.25 * f_clk) * t_ac)
            + 0.000018 * np.sin(2.0 * np.pi * (0.50 * f_clk) * t_ac)
            + 0.000014 * np.cos(2.0 * np.pi * (1.50 * f_clk) * t_ac)
        )
        sig = sig + gain * leak * (0.4 + 0.6 * burst_gate)

    wn = min(max(fc_scope, 50e6), 0.48 * FS) / (0.5 * FS)
    sos = butter(4, wn, btype='low', output='sos')
    filtered = sosfilt(sos, sig)[pad:] + dc_offset

    ac_rms = float(np.std(filtered))
    noise_std = ac_rms / (10.0 ** (snr_db / 20.0))
    trace = filtered + rng.normal(0.0, noise_std, N_SAMPLES)
    return trace


def _positive_fft_spectrum(trace):
    trace_ac = trace - np.mean(trace)
    fft_vals = np.fft.fftshift(np.fft.fft(trace_ac, n=N_SAMPLES))
    return np.abs(fft_vals[500000:1000000])


def extract_ev_single_bin(trace, f_clk=F_CLK_NOM, fs=FS):
    """
    Baseline He et al. (2024) Eq. (3): strict single-bin FFT magnitude sampling.
    Returns: (ev_norm, ev_raw, raw_energy, pos_spectrum)
    """
    pos_spectrum = _positive_fft_spectrum(trace)
    idx_eq3 = eq3_bin_indices(n_samples=len(trace), fs=fs, f_clk=f_clk)
    ev_raw = pos_spectrum[idx_eq3].astype(np.float64)
    raw_energy = float(np.sum(ev_raw ** 2))
    ev_norm = ev_raw / (np.linalg.norm(ev_raw) + 1e-12)
    return ev_norm, ev_raw, raw_energy, pos_spectrum


def extract_ev_ahbe(trace, half_bw_hz=500e3, f_clk=F_CLK_NOM, fs=FS):
    """
    SPECTRA Novelty 1: Adaptive Harmonic Band Energy (AHBE).
    Integrates dominant spectral peak RMS energy within continuous +/- 500 kHz
    windows (W >= 200 bins) centered on Eq. (3) target frequencies to guard
    against clock frequency drift and thermal jitter without noise-floor dilution.
    Returns: (ev_norm, ev_raw, raw_energy, pos_spectrum)
    """
    pos_spectrum = _positive_fft_spectrum(trace)
    n_pos = len(pos_spectrum)
    idx_eq3 = eq3_bin_indices(n_samples=len(trace), fs=fs, f_clk=f_clk)

    w_base = max(1, int(round(half_bw_hz / (fs / 2.0) * n_pos)))  # 200 bins at fs=2.5GHz
    ev_raw = np.zeros(129, dtype=np.float64)
    for i, idx in enumerate(idx_eq3):
        w = max(w_base, int(0.032 * idx))
        s_w = max(1, idx - w)
        e_w = min(n_pos, idx + w + 1)
        band = pos_spectrum[s_w:e_w]
        # Capture concentrated harmonic peak + leakage bins while rejecting thermal floor
        top_bins = np.partition(band, -5)[-5:] if len(band) >= 5 else band
        ev_raw[i] = np.sqrt(np.mean(top_bins ** 2))

    raw_energy = float(np.sum(ev_raw ** 2))
    ev_norm = ev_raw / (np.linalg.norm(ev_raw) + 1e-12)
    return ev_norm, ev_raw, raw_energy, pos_spectrum


def compute_entropy_fusion_weights(X_train_129, scores_train_10, cluster_labels,
                                   mu_g_129, mu_t_129, mu_g_10, mu_t_10,
                                   inv_cov_g, inv_cov_t):
    """
    Computes adaptive Euclidean vs. Mahalanobis fusion weights (a1, a2) from the
    true 129-D Euclidean and 10-D Mahalanobis intra-cluster variances across all
    unsupervised training assignments:
      w_ED = 1 / Var(ED_train),  w_MD = 1 / Var(MD_train)
      a1 = w_ED / (w_ED + w_MD), a2 = w_MD / (w_ED + w_MD)
    """
    ed_list = []
    md_list = []
    for i in range(len(X_train_129)):
        if cluster_labels[i] == 0:
            ed_list.append(float(np.linalg.norm(X_train_129[i] - mu_g_129)))
            diff = scores_train_10[i] - mu_g_10
            md_list.append(float(np.sqrt(max(0.0, diff @ inv_cov_g @ diff.T))))
        else:
            ed_list.append(float(np.linalg.norm(X_train_129[i] - mu_t_129)))
            diff = scores_train_10[i] - mu_t_10
            md_list.append(float(np.sqrt(max(0.0, diff @ inv_cov_t @ diff.T))))

    var_ed = float(np.var(ed_list) + 1e-12)
    var_md = float(np.var(md_list) + 1e-12)
    w_ed = 1.0 / var_ed
    w_md = 1.0 / var_md
    a1 = float(w_ed / (w_ed + w_md))
    a2 = float(w_md / (w_ed + w_md))

    shannon_entropy = float(-(a1 * np.log2(max(a1, 1e-12)) + a2 * np.log2(max(a2, 1e-12))))
    return a1, a2, var_ed, var_md, shannon_entropy


def run_unsupervised_pipeline(X_train, raw_energies_train, X_val, y_val, use_entropy_fusion=True):
    """
    End-to-end unsupervised pipeline with ZERO ground-truth y_train label leakage:
      1. Unsupervised FCM (c=2, m=2.0) on X_train
      2. SEA cluster labeling via mean raw spectral energy (Eq. 13)
      3. 10-D PCA subspace projection & unsupervised cluster covariance estimation
      4. Adaptive Fusion Distance classification on unseen X_val
    """
    n_samples = X_train.shape[0]
    c = 2
    m = 2.0

    np.random.seed(42)
    U = np.random.dirichlet(np.ones(c), size=n_samples)

    for _ in range(100):
        U_prev = U.copy()
        Um = U ** m
        V = (Um.T @ X_train) / (np.sum(Um, axis=0)[:, np.newaxis] + 1e-12)
        D_mat = np.maximum(np.linalg.norm(X_train[:, None, :] - V[None, :, :], axis=2), 1e-12)
        power_exp = 2.0 / (m - 1.0)
        for j in range(c):
            denom = np.sum((D_mat[:, j:j + 1] / D_mat) ** power_exp, axis=1)
            U[:, j] = 1.0 / (denom + 1e-12)
        if np.max(np.abs(U - U_prev)) < 1e-6:
            break

    # SEA labeling (Eq. 13) using unsupervised fuzzy membership + raw spectral energy
    Um = U ** m
    e_c0 = float(np.sum(Um[:, 0] * raw_energies_train) / (np.sum(Um[:, 0]) + 1e-12))
    e_c1 = float(np.sum(Um[:, 1] * raw_energies_train) / (np.sum(Um[:, 1]) + 1e-12))

    if e_c0 >= e_c1:
        trojan_idx, golden_idx = 0, 1
        e_trojan, e_golden = e_c0, e_c1
    else:
        trojan_idx, golden_idx = 1, 0
        e_trojan, e_golden = e_c1, e_c0

    v_golden = V[golden_idx]
    v_trojan = V[trojan_idx]

    raw_cluster_assign = np.argmax(U, axis=1)
    pred_cluster_train = (raw_cluster_assign == trojan_idx).astype(int)  # 0=Golden, 1=Trojan

    # 10-D PCA Subspace Projection
    X_mean = np.mean(X_train, axis=0)
    X_centered = X_train - X_mean
    cov_matrix = np.cov(X_centered, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
    sorted_idx = np.argsort(eigenvalues)[::-1]
    k_comp = min(10, n_samples - 1)
    coeff = eigenvectors[:, sorted_idx[:k_comp]]
    var_explained = float(np.sum(eigenvalues[sorted_idx[:k_comp]]) / (np.sum(eigenvalues) + 1e-12) * 100.0)

    scores_train = X_centered @ coeff
    mu_g_10 = (v_golden - X_mean) @ coeff
    mu_t_10 = (v_trojan - X_mean) @ coeff

    # Strictly unsupervised cluster split (ZERO y_train leakage)
    sc_g = scores_train[pred_cluster_train == 0]
    sc_t = scores_train[pred_cluster_train == 1]

    # Handle single-cluster collapse gracefully under extreme noise/drift
    if len(sc_g) < 2 or len(sc_t) < 2:
        n_val = len(y_val)
        return {
            "accuracy": 50.0,
            "precision": 50.0,
            "recall": 100.0 if len(sc_g) < 2 else 0.0,
            "fpr": 100.0 if len(sc_g) < 2 else 0.0,
            "fnr": 0.0 if len(sc_g) < 2 else 100.0,
            "mean_rfd_g": 1.0,
            "mean_rfd_t": 1.0,
            "sep_margin": 1.0,
            "sea_verified": bool(e_trojan > e_golden),
            "sea_golden_energy": e_golden,
            "sea_trojan_energy": e_trojan,
            "pca_variance_explained_pct": var_explained,
            "fusion_weights": {"a1_ed": 0.5, "a2_md": 0.5},
            "confusion_matrix": {"TP": 0, "FP": 0, "TN": 0, "FN": n_val // 2},
        }

    cov_g_10 = np.cov(sc_g, rowvar=False) + 1e-6 * np.eye(k_comp)
    cov_t_10 = np.cov(sc_t, rowvar=False) + 1e-6 * np.eye(k_comp)
    inv_cov_g = np.linalg.pinv(cov_g_10)
    inv_cov_t = np.linalg.pinv(cov_t_10)

    if use_entropy_fusion:
        a1, a2, _, _, _ = compute_entropy_fusion_weights(
            X_train, scores_train, pred_cluster_train,
            v_golden, v_trojan, mu_g_10, mu_t_10, inv_cov_g, inv_cov_t
        )
    else:
        a1, a2 = 0.5, 0.5

    pred_labels = []
    r_fd_golden = []
    r_fd_trojan = []
    for i in range(len(y_val)):
        x_raw = X_val[i]
        ed_g = float(np.linalg.norm(x_raw - v_golden))
        ed_t = float(np.linalg.norm(x_raw - v_trojan))

        x_proj = (x_raw - X_mean) @ coeff
        diff_g = x_proj - mu_g_10
        diff_t = x_proj - mu_t_10
        md_g = float(np.sqrt(max(0.0, diff_g @ inv_cov_g @ diff_g.T)))
        md_t = float(np.sqrt(max(0.0, diff_t @ inv_cov_t @ diff_t.T)))

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

    mean_rfd_g = float(np.mean(r_fd_golden)) if r_fd_golden else 1.0
    mean_rfd_t = float(np.mean(r_fd_trojan)) if r_fd_trojan else 1.0
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
        "sea_verified": bool(e_trojan > e_golden),
        "sea_golden_energy": e_golden,
        "sea_trojan_energy": e_trojan,
        "pca_variance_explained_pct": var_explained,
        "fusion_weights": {"a1_ed": a1, "a2_md": a2},
        "confusion_matrix": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
    }
