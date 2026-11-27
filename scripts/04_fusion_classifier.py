#!/usr/bin/env python3
"""
SPECTRA - Script 04: Fusion Distance Trojan Classification Engine
Reference Conformance: IEEE JIOT 2024 (Eq. 17 - Eq. 20: ED + MD Fusion Distance Ratio RFD)
Novel Enhancement: Inverse-Variance Information-Theoretic Adaptive Distance Fusion
  w_ED = 1 / Var(ED_train_129),  w_MD = 1 / Var(MD_train_10)
  a1   = w_ED / (w_ED + w_MD),   a2   = w_MD / (w_ED + w_MD)
"""

import json
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from spectra_signal_core import compute_entropy_fusion_weights

REPO_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = REPO_ROOT / "reports"
SCREENSHOTS_DIR = REPO_ROOT / "screenshots"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

print("[+] Executing SPECTRA Script 04: Fusion Distance Anomaly Classification...")

with open(REPORTS_DIR / "spectral_eigenvectors.json", "r", encoding="utf-8") as f:
    spec_data = json.load(f)
with open(REPORTS_DIR / "clustering_results.json", "r", encoding="utf-8") as f:
    cluster_data = json.load(f)
with open(REPORTS_DIR / "pca_subspace.json", "r", encoding="utf-8") as f:
    pca_data = json.load(f)

mu_G_129 = np.array(cluster_data["center_golden_129d"], dtype=np.float64)
mu_T_129 = np.array(cluster_data["center_trojan_129d"], dtype=np.float64)
cluster_pred_train = np.array(cluster_data["predicted_labels_train"], dtype=int)

X_train_129 = np.array([item["ev"] for item in spec_data["training_chips"]], dtype=np.float64)
X_mean = np.array(pca_data["x_mean_129d"], dtype=np.float64)
coeff = np.array(pca_data["coeff_matrix_129x10"], dtype=np.float64)
scores_train_10 = (X_train_129 - X_mean) @ coeff

sc_g = np.array(pca_data["sc_g_cluster"], dtype=np.float64)
sc_t = np.array(pca_data["sc_t_cluster"], dtype=np.float64)

mu_G_10 = (mu_G_129 - X_mean) @ coeff
mu_T_10 = (mu_T_129 - X_mean) @ coeff

cov_G_10 = np.cov(sc_g, rowvar=False) + 1e-6 * np.eye(10)
cov_T_10 = np.cov(sc_t, rowvar=False) + 1e-6 * np.eye(10)
inv_cov_G_10 = np.linalg.pinv(cov_G_10)
inv_cov_T_10 = np.linalg.pinv(cov_T_10)

# Adaptive Weights computed across ALL 48 unsupervised training chips in true 129-D ED & 10-D MD spaces
a1, a2, var_ed, var_md, shannon_entropy = compute_entropy_fusion_weights(
    X_train_129, scores_train_10, cluster_pred_train,
    mu_G_129, mu_T_129, mu_G_10, mu_T_10, inv_cov_G_10, inv_cov_T_10
)

print("[+] Adaptive Fusion Weight Formulation:")
print("    w_ED = 1 / Var(ED_129_train), w_MD = 1 / Var(MD_10_train)")
print("    a1 = w_ED / (w_ED + w_MD),    a2 = w_MD / (w_ED + w_MD)")
print(f"    Var(ED_129) = {var_ed:.6e}, Var(MD_10) = {var_md:.6e}, H(p) = {shannon_entropy:.6f} bits")
print(f"[+] Fusion Weights: a1 (ED) = {a1:.6f}, a2 (MD) = {a2:.6f}")

# Evaluate 24 Unseen Validation Chips
val_chips = spec_data["validation_chips"]
val_results = []
fd_g_list, fd_t_list, true_labels, pred_labels = [], [], [], []

for chip in val_chips:
    chip_id = chip["chip_id"]
    true_label = chip["label"]
    ev_129 = np.array(chip["ev"], dtype=np.float64)

    ed_g = float(np.linalg.norm(ev_129 - mu_G_129))
    ed_t = float(np.linalg.norm(ev_129 - mu_T_129))

    ev_10 = (ev_129 - X_mean) @ coeff
    diff_g = ev_10 - mu_G_10
    diff_t = ev_10 - mu_T_10
    md_g = float(np.sqrt(max(0.0, diff_g @ inv_cov_G_10 @ diff_g.T)))
    md_t = float(np.sqrt(max(0.0, diff_t @ inv_cov_T_10 @ diff_t.T)))

    fd_g = float(a1 * ed_g + a2 * md_g)
    fd_t = float(a1 * ed_t + a2 * md_t)
    r_fd = float(fd_g / (fd_t + 1e-12))
    pred_label = 1 if r_fd >= 1.0 else 0

    fd_g_list.append(fd_g)
    fd_t_list.append(fd_t)
    true_labels.append(true_label)
    pred_labels.append(pred_label)

    val_results.append({
        "chip_id": chip_id,
        "true_label": true_label,
        "predicted_label": pred_label,
        "ed_g": ed_g,
        "ed_t": ed_t,
        "md_g": md_g,
        "md_t": md_t,
        "fd_g": fd_g,
        "fd_t": fd_t,
        "r_fd": r_fd,
    })

true_labels = np.array(true_labels)
pred_labels = np.array(pred_labels)

accuracy = float(np.mean(pred_labels == true_labels) * 100.0)
tp = int(np.sum((pred_labels == 1) & (true_labels == 1)))
fp = int(np.sum((pred_labels == 1) & (true_labels == 0)))
tn = int(np.sum((pred_labels == 0) & (true_labels == 0)))
fn = int(np.sum((pred_labels == 0) & (true_labels == 1)))

precision = float(tp / (tp + fp) * 100.0 if (tp + fp) > 0 else 100.0)
recall = float(tp / (tp + fn) * 100.0 if (tp + fn) > 0 else 100.0)
fpr = float(fp / (fp + tn) * 100.0 if (fp + tn) > 0 else 0.0)

print(f"[+] SPECTRA Detection Accuracy: {accuracy:.2f}%")
print(f"[+] Precision: {precision:.2f}%, Recall: {recall:.2f}%, FPR: {fpr:.2f}%")

output_report = {
    "weight_formula": {
        "equation": "w_ED = 1/Var(ED_129), w_MD = 1/Var(MD_10); a1 = w_ED/(w_ED+w_MD), a2 = w_MD/(w_ED+w_MD)",
        "var_ed_129": var_ed,
        "var_md_10": var_md,
        "shannon_entropy_bits": shannon_entropy,
    },
    "fusion_weights": {"a1_ed": a1, "a2_md": a2},
    "metrics": {
        "accuracy_pct": accuracy,
        "precision_pct": precision,
        "recall_pct": recall,
        "false_positive_rate_pct": fpr,
        "confusion_matrix": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
    },
    "validation_chips_eval": val_results,
}

with open(REPORTS_DIR / "detection_report.json", "w", encoding="utf-8") as f:
    json.dump(output_report, f, indent=2)
print(f"[+] Saved detection report to {REPORTS_DIR / 'detection_report.json'}")

# Plot 1: Fusion Distance Decision Boundary (y = x)
fd_g_arr = np.array(fd_g_list)
fd_t_arr = np.array(fd_t_list)

fig, ax = plt.subplots(figsize=(8.0, 5.6), dpi=300)
ax.scatter(fd_g_arr[true_labels == 0], fd_t_arr[true_labels == 0],
           facecolors='none', edgecolors='#0055D4', marker='o', s=85,
           linewidth=2.0, label='Validation Golden Chips (12)')
ax.scatter(fd_g_arr[true_labels == 1], fd_t_arr[true_labels == 1],
           c='#D32F2F', marker='^', s=95,
           linewidth=1.5, label='Validation Trojan Chips (12)')

max_val = max(np.max(fd_g_arr), np.max(fd_t_arr)) * 1.15
boundary_vals = np.linspace(0, max_val, 100)
ax.plot(boundary_vals, boundary_vals, color='#00AA00', linestyle='--', linewidth=2.0,
        label='Decision Boundary "$y=x$" ($R_{FD} = 1.0$)')

ax.set_title("SPECTRA: Fusion Distance Decision Boundary ($y=x$)", fontsize=12, fontweight='bold', pad=8)
ax.set_xlabel("Distance to Golden Center ($FD_G$)", fontsize=11, fontweight='bold', fontstyle='italic', labelpad=4)
ax.set_ylabel("Distance to Trojan Center ($FD_T$)", fontsize=11, fontweight='bold', fontstyle='italic', labelpad=4)
ax.set_xlim(0, max_val)
ax.set_ylim(0, max_val)

for tick in ax.get_xticklabels() + ax.get_yticklabels():
    tick.set_fontweight('bold')
    tick.set_fontsize(10)

ax.tick_params(direction='in', top=True, right=True, length=4, width=0.8)
ax.grid(True, linestyle="--", alpha=0.4)
leg = ax.legend(loc="upper left", frameon=True, framealpha=0.95, edgecolor='black', fancybox=False, fontsize=9.5)
for text in leg.get_texts():
    text.set_fontweight('bold')

plt.tight_layout()
screenshot_path = SCREENSHOTS_DIR / "fusion_distance_classification.png"
fig.savefig(screenshot_path, dpi=300)
plt.close(fig)
print(f"[+] Saved decision boundary classification plot to {screenshot_path}")

# Plot 2: Confusion Matrix Heatmap
cm = np.array([[tn, fp], [fn, tp]], dtype=int)
fig_cm, ax_cm = plt.subplots(figsize=(6.0, 5.0), dpi=300)
im = ax_cm.imshow(cm, cmap="Blues", aspect="auto")
ax_cm.set_xticks([0, 1])
ax_cm.set_yticks([0, 1])
ax_cm.set_xticklabels(["Predicted Golden", "Predicted Trojan"], fontweight='bold')
ax_cm.set_yticklabels(["Actual Golden", "Actual Trojan"], fontweight='bold')
ax_cm.set_title(f"SPECTRA Validation Confusion Matrix (Acc: {accuracy:.1f}%)", fontsize=11, fontweight='bold', pad=10)

for r_i in range(2):
    for c_i in range(2):
        val = cm[r_i, c_i]
        txt_color = "white" if val > cm.max() / 2.0 else "black"
        ax_cm.text(c_i, r_i, f"{val}", ha="center", va="center", color=txt_color, fontsize=16, fontweight='bold')

fig_cm.colorbar(im, ax=ax_cm, fraction=0.046, pad=0.04)
plt.tight_layout()
cm_path = SCREENSHOTS_DIR / "confusion_matrix.png"
fig_cm.savefig(cm_path, dpi=300)
plt.close(fig_cm)
print(f"[+] Saved confusion matrix plot to {cm_path}")
