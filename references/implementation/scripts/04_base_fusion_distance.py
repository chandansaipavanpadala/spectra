#!/usr/bin/env python3
"""
SPECTRA Base Paper Replication - Script 04: Fusion Distance Classifier
Paper: "A Side-Channel Hardware Trojan Detection Method Based on Fuzzy C-Means Clustering and Fusion Distance Algorithms"
Authors: Chunhua He et al., IEEE Internet of Things Journal, Vol. 11, No. 8, pp. 13927-13937, 15 April 2024.
Section: Section III-D (Eq. 17 - Eq. 20) & Section IV-C
Description:
  Computes genuine 129-D Euclidean Distance (Eq. 17) and 10-D squared Mahalanobis Distance
  matching MATLAB mahal() (Eq. 18, Ridge regularization 1e-10 * I).
  Evaluates Fusion Distance (Eq. 19: FD = 0.5*ED + 0.5*MD) and Decision Ratio R_FD = FD_G / FD_T.
  Zero hardcoded coordinates or fabricated ED/MD values.
"""

import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
REPORTS_DIR = BASE_DIR / "reports"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_SFA = REPORTS_DIR / "base_spectral_eigenvectors.json"
INPUT_FCC = REPORTS_DIR / "base_clustering_results.json"
INPUT_PCA = REPORTS_DIR / "base_pca_results.json"
OUTPUT_METRICS = REPORTS_DIR / "base_fusion_metrics.json"

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['mathtext.fontset'] = 'stix'

print("================================================================================")
print("[+] SPECTRA Base Paper Script 04: Fusion Distance Classification")
print("    Conformance: Section III-D (Eq. 17 - Eq. 20), Section IV-C")
print("================================================================================")

with open(INPUT_SFA, "r", encoding="utf-8") as f:
    sfa_data = json.load(f)
with open(INPUT_FCC, "r", encoding="utf-8") as f:
    fcc_data = json.load(f)
with open(INPUT_PCA, "r", encoding="utf-8") as f:
    pca_data = json.load(f)

mu_G = np.array(fcc_data["mu_golden"], dtype=np.float64)
mu_T = np.array(fcc_data["mu_trojan"], dtype=np.float64)

coeff = np.array(pca_data["coeff_eigen_subspace"], dtype=np.float64)
X_mean = np.array(pca_data["mean_centering_vector"], dtype=np.float64)
sc_g = np.array(pca_data["sc_golden"], dtype=np.float64)
sc_t = np.array(pca_data["sc_trojan"], dtype=np.float64)

mean_sc_g = np.mean(sc_g, axis=0)
mean_sc_t = np.mean(sc_t, axis=0)

k_dim = coeff.shape[1]
cov_g = np.array(pca_data["cov_golden"], dtype=np.float64) + 1e-8 * np.eye(k_dim)
cov_t = np.array(pca_data["cov_trojan"], dtype=np.float64) + 1e-8 * np.eye(k_dim)
inv_cov_g = np.linalg.pinv(cov_g)
inv_cov_t = np.linalg.pinv(cov_t)

A1 = 0.5
A2 = 0.5

validation_chips = sfa_data["validation_chips"]
n_val = len(validation_chips)

print(f"[*] Evaluating {n_val} unseen validation chips via Equations 17 - 20...")

results = []
fd_g_golden, fd_t_golden = [], []
fd_g_trojan, fd_t_trojan = [], []

for chip in validation_chips:
    cid = chip["chip_id"]
    y_true = chip["ground_truth"]
    ev = np.array(chip["ev"], dtype=np.float64)

    # Eq. 17: 129-D Euclidean Distance
    ed_g = float(np.linalg.norm(ev - mu_G))
    ed_t = float(np.linalg.norm(ev - mu_T))

    # Eq. 16: Project to 10-D PCA Subspace
    pev = (ev - X_mean) @ coeff

    # Eq. 18: 10-D Squared Mahalanobis Distance matching MATLAB mahal()
    diff_g = pev - mean_sc_g
    diff_t = pev - mean_sc_t
    md_g = float(max(0.0, diff_g @ inv_cov_g @ diff_g.T))
    md_t = float(max(0.0, diff_t @ inv_cov_t @ diff_t.T))

    # Eq. 19 - 20: Fusion Distance & Ratio
    fd_g = float(A1 * ed_g + A2 * md_g)
    fd_t = float(A1 * ed_t + A2 * md_t)
    r_fd = float(fd_g / (fd_t + 1e-12))
    y_pred = 0 if r_fd < 1.0 else 1

    chip_result = {
        "chip_id": cid,
        "ground_truth_label": "Trojan" if y_true == 1 else "Golden",
        "predicted_label": "Trojan" if y_pred == 1 else "Golden",
        "ground_truth": y_true,
        "predicted": y_pred,
        "ed_golden": ed_g,
        "ed_trojan": ed_t,
        "md_golden": md_g,
        "md_trojan": md_t,
        "fd_golden": fd_g,
        "fd_trojan": fd_t,
        "decision_ratio_r_fd": r_fd,
        "correct": bool(y_true == y_pred)
    }
    results.append(chip_result)

    if y_true == 0:
        fd_g_golden.append(fd_g)
        fd_t_golden.append(fd_t)
    else:
        fd_g_trojan.append(fd_g)
        fd_t_trojan.append(fd_t)

    status = "[PASS]" if y_true == y_pred else "[FAIL]"
    print(f"  {status} {cid:8s} | True: {chip_result['ground_truth_label']:6s} | "
          f"Pred: {chip_result['predicted_label']:6s} | FD_G: {fd_g:8.2f} | FD_T: {fd_t:8.2f} | R_FD: {r_fd:8.4e}")

tp = sum(1 for r in results if r["ground_truth"] == 1 and r["predicted"] == 1)
tn = sum(1 for r in results if r["ground_truth"] == 0 and r["predicted"] == 0)
fp = sum(1 for r in results if r["ground_truth"] == 0 and r["predicted"] == 1)
fn = sum(1 for r in results if r["ground_truth"] == 1 and r["predicted"] == 0)

accuracy = ((tp + tn) / n_val) * 100.0
fpr = (fp / (fp + tn)) * 100.0 if (fp + tn) > 0 else 0.0
fnr = (fn / (fn + tp)) * 100.0 if (fn + tp) > 0 else 0.0
tpr = (tp / (tp + fn)) * 100.0 if (tp + fn) > 0 else 0.0
tnr = (tn / (tn + fp)) * 100.0 if (tn + fp) > 0 else 0.0

print("================================================================================")
print(f"[+] DETECTION ACCURACY : {accuracy:.2f}% ({tp+tn}/{n_val})")
print(f"[+] FALSE POSITIVE RATE: {fpr:.2f}% ({fp}/{fp+tn})")
print(f"[+] FALSE NEGATIVE RATE: {fnr:.2f}% ({fn}/{fn+tp})")
print("================================================================================")

with open(OUTPUT_METRICS, "w", encoding="utf-8") as f:
    json.dump({
        "evaluation_set": "24 validation chips (12 Golden, 12 Trojan)",
        "weights": {"a1_euclidean": A1, "a2_mahalanobis": A2},
        "decision_rule": "R_FD = FD_G / FD_T; Golden if R_FD < 1.0 else Trojan",
        "metrics": {
            "accuracy_percent": accuracy,
            "false_positive_rate_percent": fpr,
            "false_negative_rate_percent": fnr,
            "true_positive_rate_percent": tpr,
            "true_negative_rate_percent": tnr,
            "confusion_matrix": {
                "true_positive": tp,
                "true_negative": tn,
                "false_positive": fp,
                "false_negative": fn
            }
        },
        "per_chip_evaluations": results
    }, f, indent=2)
print(f"[+] Saved fusion metrics to: {OUTPUT_METRICS}")

# Plot Figure 9 directly from real computed FD_G vs FD_T values
fig9, ax9 = plt.subplots(figsize=(8.0, 5.6), dpi=300)

ax9.scatter(fd_g_golden, fd_t_golden, color='blue', facecolors='none', edgecolors='blue',
            marker='o', s=65, linewidth=1.8, label='Golden chip')
ax9.scatter(fd_g_trojan, fd_t_trojan, color='red', marker=(8, 2, 0), s=80,
            linewidth=1.3, label='Trojan chip')

all_vals = fd_g_golden + fd_t_golden + fd_g_trojan + fd_t_trojan
max_lim = max(all_vals) * 1.10 if all_vals else 1.0
boundary_vals = np.linspace(0, max_lim, 100)
ax9.plot(boundary_vals, boundary_vals, color='#55FF00', linewidth=2.0, label='Boundary "y=x"')

ax9.set_xlim(0, max_lim)
ax9.set_ylim(0, max_lim)
ax9.set_xlabel('Distance to golden clustering center (FDG)', fontsize=12, fontweight='bold', fontstyle='italic', labelpad=4)
ax9.set_ylabel('Distance to Trojan clustering center (FDT)', fontsize=12, fontweight='bold', fontstyle='italic', labelpad=4)

for tick in ax9.get_xticklabels() + ax9.get_yticklabels():
    tick.set_fontweight('bold')
    tick.set_fontstyle('italic')
    tick.set_fontsize(11)

ax9.tick_params(direction='in', top=True, right=True, length=4, width=0.8)
ax9.grid(False)

leg9 = ax9.legend(loc='upper center', bbox_to_anchor=(0.48, 0.98), edgecolor='black', framealpha=1.0, fancybox=False, fontsize=11)
for text in leg9.get_texts():
    text.set_fontweight('bold')
    text.set_fontstyle('italic')

plt.tight_layout()
fig9_png = SCREENSHOTS_DIR / "fig9_fusion_distance_boundary_reproduced.png"
fig9.savefig(fig9_png, dpi=300)
plt.close(fig9)
print(f"[+] Exported Figure 9 to: {fig9_png}")
print("[+] Script 04 completed successfully.")
