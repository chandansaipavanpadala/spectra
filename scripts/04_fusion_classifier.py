#!/usr/bin/env python3
"""
SPECTRA - Script 04: Fusion Distance Trojan Classification Engine
Reference Conformance: IEEE JIOT 2024 (Eq. 17 - Eq. 20: ED + MD Fusion Distance Ratio RFD)
Novel Enhancement: Entropy-Weighted Adaptive Distance Fusion
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg') # Headless Matplotlib execution
import matplotlib.pyplot as plt
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
SCREENSHOTS_DIR = REPO_ROOT / "screenshots"

print("[+] Executing SPECTRA Script 04: Fusion Distance Anomaly Classification...")

# Load PCA subspace & clustering data
with open(REPORTS_DIR / "spectral_eigenvectors.json", "r") as f:
    spec_data = json.load(f)

with open(REPORTS_DIR / "clustering_results.json", "r") as f:
    cluster_data = json.load(f)

with open(REPORTS_DIR / "pca_subspace.json", "r") as f:
    pca_data = json.load(f)

# Cluster centers in 129-D space
mu_G_129 = np.array(cluster_data["center_golden_129d"])
mu_T_129 = np.array(cluster_data["center_trojan_129d"])

# PCA parameters
X_mean = np.array(pca_data["x_mean_129d"])
coeff = np.array(pca_data["coeff_matrix_129x10"]) # (129, 10)
sc_g = np.array(pca_data["sc_g_24x10"])           # (24, 10)
sc_t = np.array(pca_data["sc_t_24x10"])           # (24, 10)

# Project 129-D cluster centers into 10-D PCA subspace
mu_G_10 = (mu_G_129 - X_mean) @ coeff
mu_T_10 = (mu_T_129 - X_mean) @ coeff

# Covariance matrices for 10-D Mahalanobis Distance computation
cov_G_10 = np.cov(sc_g, rowvar=False) + 1e-6 * np.eye(10)
cov_T_10 = np.cov(sc_t, rowvar=False) + 1e-6 * np.eye(10)
inv_cov_G_10 = np.linalg.pinv(cov_G_10)
inv_cov_T_10 = np.linalg.pinv(cov_T_10)

# NOVEL ENHANCEMENT: Entropy-Weighted Adaptive Distance Fusion Weights a1, a2
# Dynamically normalizes ED and MD variance across training chips
var_ed = np.var(np.linalg.norm(sc_g - mu_G_10, axis=1)) + 1e-6
var_md = np.var([np.sqrt((x - mu_G_10) @ inv_cov_G_10 @ (x - mu_G_10).T) for x in sc_g]) + 1e-6

entropy_ed = - (var_ed / (var_ed + var_md)) * np.log2(var_ed / (var_ed + var_md))
entropy_md = - (var_md / (var_ed + var_md)) * np.log2(var_md / (var_ed + var_md))

a1 = float(entropy_ed / (entropy_ed + entropy_md)) # Adaptive weight for ED
a2 = float(entropy_md / (entropy_ed + entropy_md)) # Adaptive weight for MD

print(f"[+] Entropy-Weighted Adaptive Fusion Weights: a1 (ED) = {a1:.4f}, a2 (MD) = {a2:.4f}")

# Evaluate 24 Validation Chips (12 Golden + 12 Trojan)
val_chips = spec_data["validation_chips"]
val_results = []

fd_g_list = []
fd_t_list = []
true_labels = []
pred_labels = []

for chip in val_chips:
    chip_id = chip["chip_id"]
    true_label = chip["label"]
    ev_129 = np.array(chip["ev"])

    # 1. Compute 129-D Euclidean Distances to Golden & Trojan cluster centers
    ed_g = np.linalg.norm(ev_129 - mu_G_129)
    ed_t = np.linalg.norm(ev_129 - mu_T_129)

    # 2. Project into 10-D PCA subspace
    ev_10 = (ev_129 - X_mean) @ coeff

    # 3. Compute 10-D Mahalanobis Distances
    diff_g_10 = ev_10 - mu_G_10
    diff_t_10 = ev_10 - mu_T_10
    md_g = np.sqrt(np.maximum(0.0, diff_g_10 @ inv_cov_G_10 @ diff_g_10.T))
    md_t = np.sqrt(np.maximum(0.0, diff_t_10 @ inv_cov_T_10 @ diff_t_10.T))

    # 4. Fusion Distance Calculation (Eq. 17 - Eq. 19)
    fd_g = a1 * ed_g + a2 * md_g
    fd_t = a1 * ed_t + a2 * md_t

    # 5. Fusion Distance Ratio RFD (Eq. 20)
    # Decision: RFD < 1 => Golden (0), RFD >= 1 => Trojan (1)
    r_fd = fd_g / (fd_t + 1e-12)
    pred_label = 1 if r_fd >= 1.0 else 0

    fd_g_list.append(fd_g)
    fd_t_list.append(fd_t)
    true_labels.append(true_label)
    pred_labels.append(pred_label)

    val_results.append({
        "chip_id": chip_id,
        "true_label": true_label,
        "predicted_label": pred_label,
        "ed_g": float(ed_g),
        "ed_t": float(ed_t),
        "md_g": float(md_g),
        "md_t": float(md_t),
        "fd_g": float(fd_g),
        "fd_t": float(fd_t),
        "r_fd": float(r_fd)
    })

# Compute final classification performance metrics
true_labels = np.array(true_labels)
pred_labels = np.array(pred_labels)

accuracy = np.mean(pred_labels == true_labels) * 100.0
tp = np.sum((pred_labels == 1) & (true_labels == 1))
fp = np.sum((pred_labels == 1) & (true_labels == 0))
tn = np.sum((pred_labels == 0) & (true_labels == 0))
fn = np.sum((pred_labels == 0) & (true_labels == 1))

precision = tp / (tp + fp) * 100.0 if (tp + fp) > 0 else 100.0
recall = tp / (tp + fn) * 100.0 if (tp + fn) > 0 else 100.0
fpr = fp / (fp + tn) * 100.0 if (fp + tn) > 0 else 0.0

print(f"[+] SPECTRA Detection Accuracy: {accuracy:.2f}%")
print(f"[+] Precision: {precision:.2f}%, Recall: {recall:.2f}%, FPR: {fpr:.2f}%")

# Save classification report to reports/detection_report.json
output_report = {
    "fusion_weights": {"a1_ed": a1, "a2_md": a2},
    "metrics": {
        "accuracy_pct": accuracy,
        "precision_pct": precision,
        "recall_pct": recall,
        "false_positive_rate_pct": fpr,
        "confusion_matrix": {"TP": int(tp), "FP": int(fp), "TN": int(tn), "FN": int(fn)}
    },
    "validation_chips_eval": val_results
}

with open(REPORTS_DIR / "detection_report.json", "w") as f:
    json.dump(output_report, f, indent=2)

print(f"[+] Saved detection report to {REPORTS_DIR / 'detection_report.json'}")

# Generate Screenshot Plot: Fusion Distance Classification Boundary (y = x)
fd_g_arr = np.array(fd_g_list)
fd_t_arr = np.array(fd_t_list)

plt.figure(figsize=(8, 7), dpi=300)
plt.scatter(fd_g_arr[true_labels == 0], fd_t_arr[true_labels == 0], c='#007791', marker='o', s=80, label='Validation Golden Chips (12)', alpha=0.9)
plt.scatter(fd_g_arr[true_labels == 1], fd_t_arr[true_labels == 1], c='#C0392B', marker='^', s=90, label='Validation Trojan Chips (12)', alpha=0.9)

# Decision Boundary: RFD = FD_G / FD_T = 1 => FD_T = FD_G (y = x line)
max_val = max(np.max(fd_g_arr), np.max(fd_t_arr)) * 1.15
plt.plot([0, max_val], [0, max_val], 'k--', linewidth=1.5, label='Decision Boundary (RFD = 1.0)')

plt.title("SPECTRA: Fusion Distance Classification Boundary (RFD < 1 vs RFD >= 1)", fontsize=11, fontweight='bold', pad=12)
plt.xlabel("Fusion Distance to Golden Center (FD_G)", fontsize=10, fontweight='bold')
plt.ylabel("Fusion Distance to Trojan Center (FD_T)", fontsize=10, fontweight='bold')
plt.xlim(0, max_val)
plt.ylim(0, max_val)
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend(loc="upper left", frameon=True)
plt.tight_layout()

screenshot_path = SCREENSHOTS_DIR / "fusion_distance_classification.png"
plt.savefig(screenshot_path, dpi=300)
plt.close()
print(f"[+] Saved decision boundary classification plot to {screenshot_path}")
