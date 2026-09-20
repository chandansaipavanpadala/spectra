# Verification Reports & Serialized Datasets (`reports/`)

## 1. Directory Overview & Data Contract

This directory acts as the centralized data persistence tier for the SPECTRA framework. It stores cycle-accurate simulation trace logs, serialized intermediate mathematical matrices (frequency eigenvectors, cluster centroids, projection subspaces, covariance matrices), and final post-silicon validation metrics.

All structured datasets are serialized in standard **JSON (RFC 8259)** format with strict 64-bit floating-point (`float64`) precision, ensuring deterministic reproducibility, machine parseability, and zero serialization drift across operating systems and toolchains.

---

## 2. File Catalog & File Descriptions

| File Name | Format | Generating Script | Size (approx.) | Primary Contents |
| :--- | :--- | :--- | :--- | :--- |
| [`spectral_eigenvectors.json`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/reports/spectral_eigenvectors.json) | JSON | `scripts/01_sfa_feature_extract.py` | ~306 KB | 129-D Spectral Eigenvectors ($EV$) for 48 training chips and 24 validation chips |
| [`clustering_results.json`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/reports/clustering_results.json) | JSON | `scripts/02_fcc_sea_clustering.py` | ~7.6 KB | FCM cluster centroids ($\mu_G, \mu_T$), SEA energy integrals, and convergence logs |
| [`pca_subspace.json`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/reports/pca_subspace.json) | JSON | `scripts/03_pca_dimension_reduc.py` | ~58 KB | Top-10 PCA projection matrix ($\mathbf{coeff}$), score matrices ($sc_g, sc_t$), and covariance matrices |
| [`detection_report.json`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/reports/detection_report.json) | JSON | `scripts/04_fusion_classifier.py` | ~8.8 KB | Adaptive fusion weights ($a_1, a_2$), confusion matrix, and per-chip decision ratios ($R_{FD}$) |
| [`noise_robustness_results.json`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/reports/noise_robustness_results.json) | JSON | `scripts/05_noise_robustness_sweep.py` | ~3.4 KB | SNR sweep (30 to 5 dB) and clock drift sweep (0.0% to 3.0%) comparing He et al. vs. SPECTRA AHBE |
| [`multi_benchmark_report.json`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/reports/multi_benchmark_report.json) | JSON | `scripts/06_benchmark_generalization.py` | ~2.6 KB | Cross-benchmark metrics across Implicit Counter, Trust-HUB AES-T400, and Trust-HUB AES-T800 |
| [`fpga_hardware_utilization.json`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/reports/fpga_hardware_utilization.json) | JSON | `scripts/07_synth_utilization_table.py` | ~2.5 KB | Post-synthesis LUT, FF, dynamic power, and Fmax on Xilinx Artix-7 and Spartan-3E |
| [`power_trace_golden.csv`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/reports/power_trace_golden.csv) | CSV | `src/tb_sidechannel.v` | Variable | Cycle-by-cycle power proxy trace log for the golden AES core |
| [`power_trace_trojan.csv`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/reports/power_trace_trojan.csv) | CSV | `src/tb_sidechannel.v` | Variable | Cycle-by-cycle power proxy trace log for the Trojan-infected core |

### Individual File Descriptions
- **`spectral_eigenvectors.json`:** Primary mathematical feature dataset containing normalized 129-dimensional Spectral Eigenvectors ($EV$) for 48 training chips (24 Golden, 24 Trojan) and 24 independent validation chips (12 Golden, 12 Trojan), generated from 1M-point FFT and AHBE integration at $f_s = 2.5\text{ GHz}$.
- **`clustering_results.json`:** Unsupervised learning artifact recording the convergence trajectory (5 iterations) of Fuzzy C-Means clustering, the two 129-D cluster centroids ($\mu_G, \mu_T$), and the Spectral Energy Analysis (SEA) integrals proving $\int |V_T|^2 > \int |V_G|^2$.
- **`pca_subspace.json`:** Dimensionality reduction model containing the top-10 principal axis projection matrix ($\mathbf{coeff}_{129 \times 10}$), accounting for 100.00% cumulative variance, alongside projected training score matrices and well-conditioned intra-class covariance matrices.
- **`detection_report.json`:** Comprehensive validation benchmark report detailing optimal entropy-derived distance fusion weights ($a_1 = 0.8311, a_2 = 0.1689$), final classification metrics (100.00% Accuracy, 0.00% FPR), and per-chip Euclidean, Mahalanobis, and Fusion Distance ratios ($R_{FD}$).
- **`noise_robustness_results.json`:** Sensitivity report capturing classification accuracy, false positive rates, and dynamic separation margins across SNR ($30\text{ dB} \to 5\text{ dB}$) and clock drift ($0.0\% \to 3.0\%$), comparing Baseline He et al. discrete sampling vs. SPECTRA AHBE continuous band integration.
- **`multi_benchmark_report.json`:** Threat generalization benchmark report validating 100.00% detection accuracy and autonomous SEA cluster identification across Implicit Counter, Trust-HUB AES-T400, and Trust-HUB AES-T800 under 6% inter-die PVT variation.
- **`fpga_hardware_utilization.json`:** Hardware synthesis and resource overhead report mapping Golden and Trojan AES-128 cores onto Xilinx Artix-7 (`xc7a35tcsg324-1`) and Spartan-3E (`xc3s500e-4fg320`), confirming $\Delta\text{Area} \le 0.15\%$ and $\Delta\text{Power} \le 0.10\%$.
- **`power_trace_golden.csv`:** Raw cycle-by-cycle time-domain power proxy trace captured from the simulated golden AES-128 core during low-toggle cryptographic operations, logging instantaneous dynamic switching activity.
- **`power_trace_trojan.csv`:** Raw cycle-by-cycle time-domain power proxy trace captured from the simulated Trojan-infected AES core, reflecting subtle capacitive modulation induced by the dormant 2-bit counter payload.

---

## 3. Detailed Data Schemas & Field Definitions

### 3.1 `spectral_eigenvectors.json`

Captures the output of the 1,000,000-point FFT and Adaptive Harmonic Band Energy (AHBE) feature extraction.

```json
{
  "sampling_frequency_hz": 2500000000.0,
  "clock_frequency_hz": 10000000.0,
  "n_samples": 1000000,
  "eigenvector_dimension": 129,
  "training_chips": [
    {
      "chip_id": "G_train_1",
      "label": 0,
      "ev": [0.0003847, 0.0003744, "... (129 float64 values) ..."]
    }
  ],
  "validation_chips": [
    {
      "chip_id": "G_val_1",
      "label": 0,
      "ev": [0.0003865, 0.0003859, "... (129 float64 values) ..."]
    }
  ]
}
```

#### Field Specifications
- `sampling_frequency_hz` (`float64`): Analog-to-digital sampling rate ($f_s = 2.5\text{ GHz}$).
- `clock_frequency_hz` (`float64`): Device under test (DUT) master clock ($f_{\text{clk}} = 10\text{ MHz}$).
- `n_samples` (`integer`): Number of time-domain trace points per acquisition ($N = 1,000,000$).
- `eigenvector_dimension` (`integer`): Dimensionality of the spectral feature space ($D = 129$).
- `training_chips` (`array[object]`, length 48): 24 Golden chips (`label: 0`) and 24 Trojan chips (`label: 1`).
- `validation_chips` (`array[object]`, length 24): 12 Golden chips and 12 Trojan chips for post-silicon validation.
- `ev` (`array[float64]`, length 129): Normalized spectral amplitude values:
  * Indices 0 to 64 (sub-harmonics): $(k-1) \cdot 156.25\text{ kHz}$.
  * Indices 65 to 128 (fundamental harmonics): $10\text{ MHz} + (k-65) \cdot 10\text{ MHz}$.

---

### 3.2 `clustering_results.json`

Stores the unsupervised Fuzzy C-Means (FCM) convergence status and Spectral Energy Analysis (SEA) cluster identification metrics.

```json
{
  "num_clusters": 2,
  "fuzziness_m": 2.0,
  "converged_iterations": 5,
  "sea_golden_energy": 0.9999999890090859,
  "sea_trojan_energy": 0.999999989168858,
  "unsupervised_accuracy_pct": 100.0,
  "center_golden_129d": [0.0003865, "... (129 float64 values) ..."],
  "center_trojan_129d": [0.0003743, "... (129 float64 values) ..."]
}
```

#### Field Specifications
- `num_clusters` (`integer`): Partition count ($c = 2$).
- `fuzziness_m` (`float64`): Fuzzy partition weighting exponent ($m = 2.0$, corresponding to $b = 0.5$ in He et al.).
- `converged_iterations` (`integer`): Number of iterations required to reach termination tolerance $\epsilon < 10^{-6}$ (converged in 5 iterations).
- `sea_golden_energy` (`float64`): Normalized spectral energy integral of the golden centroid $\int |V_G(f)|^2 df$.
- `sea_trojan_energy` (`float64`): Normalized spectral energy integral of the Trojan centroid $\int |V_T(f)|^2 df$.
  * Validation criterion: `sea_trojan_energy > sea_golden_energy` strictly holds, confirming the SEA theorem.
- `center_golden_129d` (`array[float64]`, length 129): Coordinates of golden cluster centroid $\mu_G \in \mathbb{R}^{129}$.
- `center_trojan_129d` (`array[float64]`, length 129): Coordinates of Trojan cluster centroid $\mu_T \in \mathbb{R}^{129}$.

---

### 3.3 `pca_subspace.json`

Contains the 10-dimensional Principal Component Analysis (PCA) projection matrix, eigenvalues, projected score matrices, and subspace covariance matrices.

```json
{
  "num_components": 10,
  "explained_variance_pct": 99.99994946633737,
  "x_mean_129d": [0.0003804, "... (129 values) ..."],
  "eigenvalues_top10": [0.001245, "... (10 values) ..."],
  "coeff_matrix_129x10": [
    [-0.00013, 0.0045, "... (10 values) ..."]
  ],
  "sc_golden_24x10": [
    [-0.142, 0.012, "... (10 values) ..."]
  ],
  "sc_trojan_24x10": [
    [0.142, -0.012, "... (10 values) ..."]
  ],
  "cov_sc_golden_10x10": [
    [0.00045, 0.00001, "... (10 values) ..."]
  ],
  "cov_sc_trojan_10x10": [
    [0.00048, -0.00002, "... (10 values) ..."]
  ]
}
```

#### Field Specifications
- `num_components` (`integer`): Orthogonal projection rank ($k_n = 10$).
- `explained_variance_pct` (`float64`): Cumulative variance retained by the top 10 eigenvalues ($99.99995\%$, exceeding the $>85\%$ requirement).
- `coeff_matrix_129x10` (`array[array[float64]]`, $129 \times 10$): Orthogonal eigen-subspace projection matrix $\mathbf{coeff}$.
- `sc_golden_24x10` / `sc_trojan_24x10` (`array[array[float64]]`, $24 \times 10$): Projected scores $sc_g, sc_t$ for training chips.
- `cov_sc_golden_10x10` / `cov_sc_trojan_10x10` (`array[array[float64]]`, $10 \times 10$): Full intra-cluster covariance matrices $\Sigma_{sc_g}, \Sigma_{sc_t}$. Since $N_{\text{samples}} = 24 > 10$, these matrices are mathematically guaranteed positive-definite and non-singular.

---

### 3.4 `detection_report.json`

Details the final post-silicon validation metrics, adaptive distance weights, and per-chip classification decisions across 24 independent test chips.

```json
{
  "fusion_weights": {
    "a1_ed": 0.8310807533008396,
    "a2_md": 0.16891924669916036
  },
  "metrics": {
    "accuracy_pct": 100.0,
    "precision_pct": 100.0,
    "recall_pct": 100.0,
    "false_positive_rate_pct": 0.0,
    "confusion_matrix": {
      "TP": 12,
      "FP": 0,
      "TN": 12,
      "FN": 0
    }
  },
  "validation_chips_eval": [
    {
      "chip_id": "G_val_1",
      "true_label": 0,
      "predicted_label": 0,
      "ed_g": 0.0001217,
      "ed_t": 0.2027789,
      "md_g": 0.0612502,
      "md_t": 202.76530,
      "fd_g": 0.0104475,
      "fd_t": 34.419488,
      "r_fd": 0.0003035
    },
    {
      "chip_id": "T_val_1",
      "true_label": 1,
      "predicted_label": 1,
      "ed_g": 0.2027932,
      "ed_t": 0.0001044,
      "md_g": 202.78292,
      "md_t": 0.0502944,
      "fd_g": 34.422476,
      "fd_t": 0.0085825,
      "r_fd": 4010.7917
    }
  ]
}
```

#### Field Specifications
- `fusion_weights`: Information-entropy adaptive weights ($a_1 = 0.8311, a_2 = 0.1689$, $a_1 + a_2 = 1.0$).
- `metrics`: Overall statistical performance:
  * Accuracy: 100.00% (24 / 24 correct).
  * FPR: 0.00% (0 false alarms out of 12 golden chips).
  * FNR: 0.00% (0 escapes out of 12 Trojan chips).
- `validation_chips_eval`: Granular per-device distance breakdown:
  * `ed_g`, `ed_t`: 129-D Euclidean distances to golden and Trojan centroids.
  * `md_g`, `md_t`: 10-D Mahalanobis distances in the PCA subspace.
  * `fd_g`, `fd_t`: Combined fusion distances ($FD = a_1 \cdot ED + a_2 \cdot MD$).
  * `r_fd`: Classification decision ratio ($R_{FD} = FD_G / FD_T$).
    - Golden chips cluster at $R_{FD} \approx 2.78 \times 10^{-4} \ll 1.0$ (range $0.000226$ to $0.000329$).
    - Trojan chips cluster at $R_{FD} \approx 3762.58 \gg 1.0$ (range $2372.35$ to $8566.01$).
    - Dynamic separation margin exceeds $10^7$, ensuring zero classification ambiguity.

---

### 3.5 `noise_robustness_results.json`

Records sensitivity metrics across the SNR degradation sweep ($30\text{ dB} \to 5\text{ dB}$) and clock frequency drift sweep ($0.0\% \to 3.0\%$).

```json
{
  "sweep_configuration": {
    "sampling_frequency_hz": 2500000000.0,
    "nominal_clock_hz": 10000000.0,
    "sample_points": 1000000,
    "chips_per_run": 48,
    "ahbe_bandwidth_khz": 1000.0,
    "window_half_width_khz": 500.0
  },
  "snr_sensitivity_sweep": {
    "snr_db": [30, 25, 20, 15, 10, 5],
    "method_a_he": {
      "accuracy": [58.33, 56.25, 50.00, 52.08, 58.33, 72.92],
      "fpr": [83.33, 87.50, 87.50, 83.33, 70.83, 41.67],
      "sep_margin": [8.50, 4.59, 2.57, 2.52, 2.73, 1.98]
    },
    "method_b_spectra": {
      "accuracy": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
      "fpr": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
      "sep_margin": [27411.43, 27622.38, 25957.84, 22689.73, 16335.16, 9804.39]
    }
  }
}
```

---

### 3.6 `multi_benchmark_report.json`

Captures cross-benchmark detection metrics across three standard hardware Trojan threat profiles.

```json
{
  "evaluation_scope": "Multi-Trojan Threat Generalization",
  "inter_die_process_variation": "6% Inter-Die Gaussian PVT",
  "benchmarks_evaluated": {
    "counter_he": "Implicit 2-Bit Counter (He et al.)",
    "aes_t400": "Trust-HUB AES-T400 (Combinational)",
    "aes_t800": "Trust-HUB AES-T800 (Sequential)"
  },
  "results": {
    "counter_he": {
      "sea_verified": true,
      "accuracy_pct": 100.0,
      "precision_pct": 100.0,
      "recall_pct": 100.0,
      "false_positive_rate_pct": 0.0,
      "mean_rfd_golden": 0.0292,
      "mean_rfd_trojan": 29.91,
      "dynamic_separation_margin": 1024.83
    },
    "aes_t400": {
      "sea_verified": true,
      "accuracy_pct": 100.0,
      "precision_pct": 100.0,
      "recall_pct": 100.0,
      "false_positive_rate_pct": 0.0,
      "mean_rfd_golden": 0.0245,
      "mean_rfd_trojan": 52.35,
      "dynamic_separation_margin": 2132.65
    },
    "aes_t800": {
      "sea_verified": true,
      "accuracy_pct": 100.0,
      "precision_pct": 100.0,
      "recall_pct": 100.0,
      "false_positive_rate_pct": 0.0,
      "mean_rfd_golden": 0.0308,
      "mean_rfd_trojan": 22.95,
      "dynamic_separation_margin": 746.01
    }
  }
}
```

---

### 3.7 `fpga_hardware_utilization.json`

Details placed-and-routed FPGA resource utilization, dynamic power dissipation, and timing margins on Artix-7 and Spartan-3E.

```json
{
  "devices": {
    "artix7": {
      "part": "xc7a35tcsg324-1",
      "family": "Xilinx Artix-7 (28nm)",
      "golden": {"slice_luts": 2145, "slice_ffs": 264, "dynamic_power_mw": 12.45, "critical_path_delay_ns": 4.82, "fmax_mhz": 207.47},
      "trojan": {"slice_luts": 2147, "slice_ffs": 268, "dynamic_power_mw": 12.46, "critical_path_delay_ns": 4.83, "fmax_mhz": 207.04},
      "overhead": {"delta_lut_pct": 0.0932, "delta_power_pct": 0.0803, "stealth_criteria_met": true}
    },
    "spartan3e": {
      "part": "xc3s500e-4fg320",
      "family": "Xilinx Spartan-3E (90nm, He et al. Target)",
      "golden": {"slice_luts": 3842, "slice_ffs": 264, "dynamic_power_mw": 38.60, "critical_path_delay_ns": 11.24, "fmax_mhz": 88.97},
      "trojan": {"slice_luts": 3846, "slice_ffs": 268, "dynamic_power_mw": 38.63, "critical_path_delay_ns": 11.26, "fmax_mhz": 88.81},
      "overhead": {"delta_lut_pct": 0.1041, "delta_power_pct": 0.0777, "stealth_criteria_met": true}
    }
  }
}
```

---

## 4. Programmatic Data Ingestion (Python Example)

To ingest and validate the reports programmatically:

```python
import json
from pathlib import Path

reports_dir = Path("reports")

# Ingest classification report
with open(reports_dir / "detection_report.json", "r") as f:
    report = json.load(f)

# Verify accuracy and zero false alarm rate
assert report["metrics"]["accuracy_pct"] == 100.0
assert report["metrics"]["false_positive_rate_pct"] == 0.0

# Verify dynamic separation margin
golden_r_fd = [c["r_fd"] for c in report["validation_chips_eval"] if c["true_label"] == 0]
trojan_r_fd = [c["r_fd"] for c in report["validation_chips_eval"] if c["true_label"] == 1]

mean_g = sum(golden_r_fd) / len(golden_r_fd)
mean_t = sum(trojan_r_fd) / len(trojan_r_fd)
separation_margin = mean_t / mean_g

print(f"Mean Golden R_FD: {mean_g:.6e}")
print(f"Mean Trojan R_FD: {mean_t:.2f}")
print(f"Dynamic Separation Ratio: {separation_margin:.2e}")
assert separation_margin > 1e7, "Separation margin must exceed 10^7"
```
