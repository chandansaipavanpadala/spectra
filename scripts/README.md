# Execution Scripts & Automation Suite (`scripts/`)

## 1. Directory Overview & Software Architecture

This directory contains the end-to-end Python algorithmic processing pipeline and Xilinx Vivado Tcl automation scripts for the SPECTRA framework. 

The software architecture is decoupled into discrete, deterministic stages following a strictly directed acyclic graph (DAG) execution model:
1. **Feature Extraction:** Time-domain trace generation, Discrete Fourier Transform (DFT), and Adaptive Harmonic Band Energy (AHBE) eigenvector construction.
2. **Unsupervised Clustering:** Vectorized Fuzzy C-Means (FCM) clustering and autonomous Spectral Energy Analysis (SEA) cluster labeling.
3. **Dimensionality Reduction:** 10-D Principal Component Analysis (PCA) subspace orthogonal projection.
4. **Distance Metric Learning & Classification:** Information-Entropy adaptive distance fusion ($ED + MD$) and validation decision thresholding.
5. **EDA Tool Automation:** Headless Vivado batch synthesis, elaboration, and schematic capture.

---

## 2. File Manifest & File Descriptions

| Script Name | Environment | Execution Stage | Upstream Input Dependencies | Generated Output Artifacts |
| :--- | :--- | :--- | :--- | :--- |
| [`01_sfa_feature_extract.py`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/scripts/01_sfa_feature_extract.py) | Python 3.10+ | Step 1 | Simulation parameters ($f_s, f_{\text{clk}}$) | `reports/spectral_eigenvectors.json`<br>`screenshots/time_domain_traces.png`<br>`screenshots/sfa_spectrum_comparison.png` |
| [`02_fcc_sea_clustering.py`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/scripts/02_fcc_sea_clustering.py) | Python 3.10+ | Step 2 | `reports/spectral_eigenvectors.json` | `reports/clustering_results.json` |
| [`03_pca_dimension_reduc.py`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/scripts/03_pca_dimension_reduc.py) | Python 3.10+ | Step 3 | `reports/spectral_eigenvectors.json`<br>`reports/clustering_results.json` | `reports/pca_subspace.json`<br>`screenshots/pca_3d_clusters.png` |
| [`04_fusion_classifier.py`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/scripts/04_fusion_classifier.py) | Python 3.10+ | Step 4 | `reports/spectral_eigenvectors.json`<br>`reports/clustering_results.json`<br>`reports/pca_subspace.json` | `reports/detection_report.json`<br>`screenshots/fusion_distance_classification.png`<br>`screenshots/confusion_matrix.png` |
| [`05_noise_robustness_sweep.py`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/scripts/05_noise_robustness_sweep.py) | Python 3.10+ | Step 5 | Simulation parameters ($f_s, f_{\text{clk}}$, SNR, drift) | `reports/noise_robustness_results.json`<br>`screenshots/noise_robustness_sweep.png` |
| [`06_benchmark_generalization.py`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/scripts/06_benchmark_generalization.py) | Python 3.10+ | Step 6 | Benchmark definitions (Counter, AES-T400, AES-T800) | `reports/multi_benchmark_report.json`<br>`screenshots/benchmark_comparison.png` |
| [`07_synth_utilization_table.py`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/scripts/07_synth_utilization_table.py) | Python 3.10+ | Step 7 | `src/aes_128.v`<br>`src/aes_128_trojan.v` | `reports/fpga_hardware_utilization.json`<br>Terminal utilization tables |
| [`export_screenshots.tcl`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/scripts/export_screenshots.tcl) | Vivado Tcl | EDA Batch | `src/aes_128.v`<br>`src/aes_128_trojan.v` | Elaborated RTL netlists & schematics |
| [`recreate_project.tcl`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/scripts/recreate_project.tcl) | Vivado Tcl | Project Build | `src/*.v`<br>`constraints/*.xdc` | Regenerated Vivado project (`spectra.xpr`) |

### Individual File Descriptions
- **`01_sfa_feature_extract.py`:** Generates 1M-point time-domain power proxy traces with realistic clock harmonics, inter-die PVT drift, and thermal noise; computes 1M-point FFT with spectrum shifting; integrates Adaptive Harmonic Band Energy (AHBE) across continuous symmetric $\pm 500\text{ kHz}$ windows; and serializes 129-D eigenvectors for 48 training chips and 24 validation chips.
- **`02_fcc_sea_clustering.py`:** Implements vectorized Fuzzy C-Means (FCM) clustering ($c=2, m=2.0$) to partition unlabelled training chips; applies the Spectral Energy Analysis (SEA) theorem to autonomously designate the higher-energy centroid as Trojan and the lower as Golden; and exports cluster centers.
- **`03_pca_dimension_reduc.py`:** Performs sample covariance decomposition via SVD on centered spectral eigenmatrices; projects 129-D features onto the top $k_n = 10$ principal components (retaining 100.00% cumulative variance); constructs invertible intra-class subspace covariance matrices; and renders 3D cluster visualizations.
- **`04_fusion_classifier.py`:** Computes 129-D Euclidean and 10-D Mahalanobis distances for validation chips; calculates information-entropy adaptive fusion weights ($a_1 = 0.8311, a_2 = 0.1689$); evaluates the decision ratio $R_{FD} = FD_G / FD_T$ against threshold 1.0; and outputs classification metrics and decision plane figures.
- **`05_noise_robustness_sweep.py`:** Evaluates PVT noise resilience and clock frequency drift immunity across $P = 48$ chips per condition. Sweeps SNR ($30\text{ dB} \to 5\text{ dB}$) and clock drift ($0.0\% \to 3.0\%$), comparing Baseline He et al. (single-bin) vs. SPECTRA AHBE (continuous band), and exports dual-panel 300 DPI publication plots.
- **`06_benchmark_generalization.py`:** Validates cross-benchmark generalizability across three standard hardware Trojan threat classes (Implicit Counter, Trust-HUB AES-T400 combinational trigger, Trust-HUB AES-T800 sequential time-bomb) under 6% inter-die PVT variation.
- **`07_synth_utilization_table.py`:** Performs post-synthesis FPGA hardware resource modeling across Xilinx Artix-7 (`xc7a35tcsg324-1`) and Spartan-3E (`xc3s500e-4fg320`), verifying area overhead $\Delta\text{Area} \le 0.15\%$ and dynamic power overhead $\Delta\text{Power} \le 0.10\%$.
- **`export_screenshots.tcl`:** Headless Vivado batch automation script that creates an in-memory project, reads the RTL source modules, elaborates the netlists, checks syntax, and exports graphical schematic diagrams of the synthesized AES cores.
- **`recreate_project.tcl`:** Complete Vivado Tcl build automation script that re-creates the active GUI project (`spectra.xpr`), establishes `sources_1`, `constrs_1`, and `sim_1` filesets, and sets compiler properties for reproducible FPGA implementation.

---

## 3. Python Pipeline Module Documentation

### 3.1 `01_sfa_feature_extract.py` (Spectral Feature Analysis & AHBE)

#### Operational Workflow
1. **Time-Domain Signal Synthesis (`generate_chip_trace`):**
   - Synthesizes 1,000,000-point time-domain traces at $f_s = 2.5\text{ GHz}$ ($400\text{ ps}$ step size) over a 10 MHz clock fundamental ($100\text{ ns}$ period).
   - Incorporates clock harmonics ($10, 20, 30, 40\text{ MHz}$), Process-Voltage-Temperature (PVT) background inter-die drift ($\sigma = 0.003$), and additive Gaussian thermal noise ($\sigma = 0.015$).
   - For Trojan chips, modulates localized capacitive switching at inter-harmonic frequencies ($15, 25, 35\text{ MHz}$) corresponding to the 2-bit counter payload.
2. **Frequency Domain Transformation:**
   - Computes 1M-point Discrete Fourier Transform via vectorized `np.fft.fft`.
   - Centers the zero-frequency DC component via `np.fft.fftshift`.
   - Slices the positive spectrum $Y = D[500,001 : 1,000,000]$ spanning $0$ to $1.25\text{ GHz}$ ($\Delta f = 2500\text{ Hz}$).
3. **Adaptive Harmonic Band Energy (AHBE) Integration:**
   - Evaluates sub-harmonic bins ($k = 1 \dots 65$) across fractional multiples $(k-1) \cdot 156.25\text{ kHz}$.
   - Evaluates harmonic bins ($k = 66 \dots 129$) across $10\text{ MHz} + (k-65) \cdot 10\text{ MHz}$.
   - Calculates continuous root-mean-square spectral energy across a $\pm 500\text{ kHz}$ symmetric band around each harmonic peak to prevent clock jitter attenuation.
4. **Dataset Serialization:**
   - Constructs $48$ training chips (24 Golden, 24 Trojan) and $24$ validation chips (12 Golden, 12 Trojan), serializing the complete set to [`reports/spectral_eigenvectors.json`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/reports/spectral_eigenvectors.json).

---

### 3.2 `02_fcc_sea_clustering.py` (Fuzzy C-Means & Spectral Energy Analysis)

#### Operational Workflow
1. **Vectorized Fuzzy C-Means Optimization:**
   - Ingests the 48-chip training matrix $X \in \mathbb{R}^{48 \times 129}$.
   - Initializes random membership matrix $U \in \mathbb{R}^{48 \times 2}$ satisfying $\sum_{j=1}^2 u_{ij} = 1$.
   - Iteratively updates centroids $V_j \in \mathbb{R}^{129}$ and fuzzy memberships $u_{ij}$ with weighting exponent $m = 2.0$:
     $$u_{ij} = \frac{1}{\sum_{k=1}^2 \left(\frac{\|X_i - V_j\|_2}{\|X_i - V_k\|_2}\right)^2}$$
   - Convergence is reached when $\max |U^{(t)} - U^{(t-1)}| < 10^{-6}$ (converges in 5 iterations).
2. **Spectral Energy Analysis (SEA) Theorem Execution:**
   - Evaluates the continuous energy integral numerically using the trapezoidal rule:
     $$E_j = \int_0^{f_{\max}} |V_j(f)|^2 df \approx \sum_{k=1}^{129} V_j[k]^2$$
   - Theorem verification: $\int |V_T|^2 = 0.999999989169 > \int |V_G|^2 = 0.999999989009$.
   - The cluster centroid with greater integral energy is designated as $\mu_T$ (Trojan), and the lesser as $\mu_G$ (Golden).
3. **Serialization:**
   - Exports centroids and convergence metrics to [`reports/clustering_results.json`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/reports/clustering_results.json).

---

### 3.3 `03_pca_dimension_reduc.py` (10-D PCA Subspace Projection)

#### Operational Workflow
1. **Covariance Decomposition:**
   - Centers the 48-chip training matrix: $\bar{X} = X - \mu_X$.
   - Calculates the sample covariance matrix $\Sigma = \frac{1}{P-1} \bar{X}^T \bar{X} \in \mathbb{R}^{129 \times 129}$.
   - Computes singular value decomposition (SVD) or eigendecomposition (`np.linalg.eigh`), sorting eigenvalues in descending order.
2. **Eigen-Subspace Selection:**
   - Extracts the top $k_n = 10$ principal components.
   - Cumulative variance explained reaches **99.99995% (100.00%)**, surpassing the IEEE JIOT 2024 $>85\%$ threshold.
   - Computes projection matrix $\mathbf{coeff} \in \mathbb{R}^{129 \times 10}$.
3. **Score Matrix & Covariance Generation:**
   - Projects Golden and Trojan training matrices: $sc_g = \bar{X}_{\text{golden}} \times \mathbf{coeff}$, $sc_t = \bar{X}_{\text{trojan}} \times \mathbf{coeff} \in \mathbb{R}^{24 \times 10}$.
   - Evaluates intra-class subspace covariance matrices $\Sigma_{sc_g}, \Sigma_{sc_t} \in \mathbb{R}^{10 \times 10}$. Because $24 > 10$, these matrices are guaranteed non-singular and well-conditioned for Mahalanobis inversion.
4. **Serialization & 3D Plotting:**
   - Exports the eigenspace model to [`reports/pca_subspace.json`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/reports/pca_subspace.json).
   - Generates 3D cluster plot [`screenshots/pca_3d_clusters.png`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/screenshots/pca_3d_clusters.png).

---

### 3.4 `04_fusion_classifier.py` (Adaptive Fusion Distance Classifier)

#### Operational Workflow
1. **Distance Metric Evaluation:**
   - For each validation device $X_{\text{val}} \in \mathbb{R}^{129}$ and its projection $PEV \in \mathbb{R}^{10}$:
     * $ED_G = \|X_{\text{val}} - \mu_G\|_2$, $ED_T = \|X_{\text{val}} - \mu_T\|_2$.
     * $MD_G = \sqrt{(PEV - \mu_{sc_g}) \Sigma_{sc_g}^{-1} (PEV - \mu_{sc_g})^T}$.
     * $MD_T = \sqrt{(PEV - \mu_{sc_t}) \Sigma_{sc_t}^{-1} (PEV - \mu_{sc_t})^T}$.
2. **Information-Entropy Adaptive Weighting:**
   - Solves the heuristic weighting limitation of He et al. by deriving weights from intra-cluster distance variance and Shannon entropy:
     $$w_1 = \frac{1}{\text{Var}(ED)}, \quad w_2 = \frac{1}{\text{Var}(MD)}$$
     $$a_1 = 0.8311, \quad a_2 = 0.1689$$
3. **Fusion Decision Axiom:**
   - Evaluates $FD_G = a_1 ED_G + a_2 MD_G$ and $FD_T = a_1 ED_T + a_2 MD_T$.
   - Computes decision ratio: $R_{FD} = \frac{FD_G}{FD_T}$.
   - Golden if $R_{FD} < 1.0$; Trojan if $R_{FD} \ge 1.0$.
4. **Validation Reporting & Plotting:**
   - Validates all 24 test chips (12 Golden, 12 Trojan), achieving 100.00% accuracy and 0.00% False Positive Rate.
   - Serializes complete per-chip breakdown to [`reports/detection_report.json`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/reports/detection_report.json).
   - Generates decision boundary plot [`screenshots/fusion_distance_classification.png`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/screenshots/fusion_distance_classification.png) and [`screenshots/confusion_matrix.png`](file:///p:/OneDrive%20-%20Amrita%20vishwa%20vidyapeetham/ASEB/B.Tech/4th%20Year/7th%20Semester/Hardware%20Security%20and%20Trust/Project/spectra/screenshots/confusion_matrix.png).

---

### 3.5 `05_noise_robustness_sweep.py` (PVT & SNR Sensitivity Sweep)

#### Operational Workflow
1. **Stress-Test Configuration:**
   - Ingests 1M-point traces at $f_s = 2.5\text{ GHz}$ ($f_{\text{clk}} = 10\text{ MHz}$).
   - Sweeps Signal-to-Noise Ratio (SNR) across $[30, 25, 20, 15, 10, 5]\text{ dB}$.
   - Concurrently sweeps oscillator frequency drift across $[0.0\%, 0.5\%, 1.0\%, 1.5\%, 2.0\%, 2.5\%, 3.0\%]$ to simulate phase jitter and thermal drift.
2. **Methodological Comparison:**
   - Evaluates **Method A (Baseline He et al.)** using single-bin sampling against **Method B (SPECTRA AHBE)** integrating symmetric $\pm 500\text{ kHz}$ bands across 48 chips per step.
   - Executes full downstream pipeline (FCM $\to$ SEA $\to$ 10-D PCA $\to$ Fusion Distance).
3. **Key Findings:**
   - He et al. single-bin sampling degrades to $50.0\%$--$72.9\%$ accuracy as clock drift shifts harmonics away from nominal bins.
   - SPECTRA AHBE preserves $100.00\%$ accuracy and $0.00\%$ FPR across all conditions down to $5\text{ dB}$ SNR with separation margins $>9.8 \times 10^3$.

---

### 3.6 `06_benchmark_generalization.py` (Multi-Trojan Benchmark Validation)

#### Operational Workflow
1. **Threat Class Taxonomy:**
   - **Benchmark 1 (`Implicit Counter`):** Synchronous 2-bit counter payload modulating inter-harmonic side-bands at 15, 25, 35 MHz (He et al. baseline).
   - **Benchmark 2 (`Trust-HUB AES-T400`):** Rare 32-bit state comparator inducing supply rail droop ($\Delta V_{\text{dd}}$) and transient harmonic redistribution.
   - **Benchmark 3 (`Trust-HUB AES-T800`):** Sequential time-bomb counter leaking cryptographic key bits via periodic capacitive switching bursts.
2. **Generalization Validation:**
   - Evaluates 48 training chips and 24 validation chips per benchmark under 6% inter-die PVT power variation.
   - Confirms the Spectral Energy Analysis (SEA) theorem ($\int |V_T|^2 > \int |V_G|^2$) across all threat classes.
   - Achieves $100.00\%$ accuracy, $100.00\%$ precision, $100.00\%$ recall, and $0.00\%$ FPR across all three benchmarks.

---

### 3.7 `07_synth_utilization_table.py` (FPGA Area & Power Synthesis)

#### Operational Workflow
1. **Target Technology Analysis:**
   - Targets Xilinx Artix-7 (`xc7a35tcsg324-1`, 28nm) and Spartan-3E (`xc3s500e-4fg320`, 90nm).
   - Ingests and parses `src/aes_128.v` and `src/aes_128_trojan.v`.
2. **Resource & Timing Extraction:**
   - Evaluates Slice LUTs, Slice Registers/FFs, Dynamic Power at 10 MHz, $F_{\max}$, and critical path delay.
   - Verifies stealth constraints: $\Delta\text{Area} = +0.0932\%$ on Artix-7 and $+0.1041\%$ on Spartan-3E ($\le 0.15\%$ bound); $\Delta\text{Power} = +0.0803\%$ and $+0.0777\%$ ($\le 0.10\%$ bound).

---

## 4. Vivado Tcl Automation Scripts

### 4.1 `export_screenshots.tcl`
Executes headless batch synthesis and schematic generation:
```bash
vivado -mode batch -source scripts/export_screenshots.tcl
```
- Creates an in-memory project targeting Xilinx Artix-7 (`xc7a35tcsg324-1`).
- Synthesizes `src/aes_128.v` and `src/aes_128_trojan.v`.
- Elaborates RTL netlists and verifies zero syntax or port mismatch warnings.

### 4.2 `recreate_project.tcl`
Recreates the complete Vivado IDE project with associated filesets and run configurations:
```bash
vivado -mode tcl -source scripts/recreate_project.tcl
```
- Creates project `spectra.xpr` in `./spectra_prj/`.
- Configures `sources_1`, `constrs_1`, and `sim_1` filesets.
- Sets synthesis and implementation strategies optimized for area and timing closure.

---

## 5. Software Requirements & Reproduction Commands

All scripts require Python 3.10 or newer with standard scientific computing packages:
```bash
pip install numpy matplotlib scipy
```

To run the complete pipeline sequentially:
```bash
python scripts/01_sfa_feature_extract.py
python scripts/02_fcc_sea_clustering.py
python scripts/03_pca_dimension_reduc.py
python scripts/04_fusion_classifier.py
python scripts/05_noise_robustness_sweep.py
python scripts/06_benchmark_generalization.py
python scripts/07_synth_utilization_table.py
```
All scripts execute deterministically and generate verified output files inside `reports/` and `screenshots/`.
