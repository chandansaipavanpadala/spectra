#!/usr/bin/env python3
"""
SPECTRA Base Paper Replication - Script 03: PCA Dimensionality Reduction
Paper: "A Side-Channel Hardware Trojan Detection Method Based on Fuzzy C-Means Clustering and Fusion Distance Algorithms"
Authors: Chunhua He et al., IEEE Internet of Things Journal, Vol. 11, No. 8, pp. 13927-13937, 15 April 2024.
Section: Section III-C (Eq. 14 - Eq. 16) & Section IV-C
Description:
  Reduces 129-D spectral eigenvectors to kn = 10 principal components via SVD.
  Splits scores strictly using unsupervised cluster assignments from Script 02.
  Plots Figure 8 directly from genuine sc_golden[:, :3] and sc_trojan[:, :3] projections
  and true cluster centroids (zero hardcoded coordinates).
"""

import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
REPORTS_DIR = BASE_DIR / "reports"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_SFA = REPORTS_DIR / "base_spectral_eigenvectors.json"
INPUT_FCC = REPORTS_DIR / "base_clustering_results.json"
OUTPUT_PCA = REPORTS_DIR / "base_pca_results.json"

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['mathtext.fontset'] = 'stix'

print("================================================================================")
print("[+] SPECTRA Base Paper Script 03: PCA Dimensionality Reduction")
print("    Conformance: Section III-C (Eq. 14 - Eq. 16), Section IV-C")
print("================================================================================")

with open(INPUT_SFA, "r", encoding="utf-8") as f:
    sfa_data = json.load(f)

with open(INPUT_FCC, "r", encoding="utf-8") as f:
    fcc_data = json.load(f)

golden_ids = set(fcc_data["golden_cluster_indices"])
trojan_ids = set(fcc_data["trojan_cluster_indices"])
training_chips = sfa_data["training_chips"]

EX_G = np.array([chip["ev"] for chip in training_chips if chip["chip_id"] in golden_ids], dtype=np.float64)
EX_T = np.array([chip["ev"] for chip in training_chips if chip["chip_id"] in trojan_ids], dtype=np.float64)

n_g = len(EX_G)
n_t = len(EX_T)
N_CHIPS = n_g + n_t
P_VARS = EX_G.shape[1]

X = np.vstack([EX_G, EX_T])
print(f"[*] Input Spectral Matrix X: {X.shape[0]} chips x {X.shape[1]} spectral variables.")

# PCA (Eq. 14): Center and decompose via SVD
KN = 10
X_mean = np.mean(X, axis=0)
X_centered = X - X_mean
_, S, Vt = np.linalg.svd(X_centered, full_matrices=False)

coeff = Vt[:KN, :].T
sc = X_centered @ coeff
lat = (S ** 2) / max(1, N_CHIPS - 1)
epl = (lat[:KN] / np.sum(lat)) * 100.0
cumulative_variance_explained = float(np.sum(epl))
compression_ratio = (KN / P_VARS) * 100.0

print(f"[+] PCA Compression Ratio: {compression_ratio:.2f}% | Cumulative Variance (10 PCs): {cumulative_variance_explained:.2f}%")

sc_g = sc[:n_g, :]
sc_t = sc[n_g:, :]
center_g_pca = np.mean(sc_g, axis=0)
center_t_pca = np.mean(sc_t, axis=0)
cov_g = np.cov(sc_g, rowvar=False) if n_g > 1 else np.eye(KN)
cov_t = np.cov(sc_t, rowvar=False) if n_t > 1 else np.eye(KN)

with open(OUTPUT_PCA, "w", encoding="utf-8") as f:
    json.dump({
        "kn_components": KN,
        "input_dimension_p": P_VARS,
        "data_compression_ratio_percent": compression_ratio,
        "cumulative_variance_explained_percent": cumulative_variance_explained,
        "variance_explained_per_component_percent": epl.tolist(),
        "mean_centering_vector": X_mean.tolist(),
        "coeff_eigen_subspace": coeff.tolist(),
        "sc_golden": sc_g.tolist(),
        "sc_trojan": sc_t.tolist(),
        "pca_center_golden": center_g_pca.tolist(),
        "pca_center_trojan": center_t_pca.tolist(),
        "cov_golden": cov_g.tolist(),
        "cov_trojan": cov_t.tolist()
    }, f, indent=2)
print(f"[+] Saved PCA results to: {OUTPUT_PCA}")

# Plot Figure 8 directly from genuine 3D PCA coordinates and true cluster centroids
fig8 = plt.figure(figsize=(8.0, 6.8), dpi=300)
ax8 = fig8.add_subplot(111, projection='3d')

ax8.xaxis.pane.fill = False
ax8.yaxis.pane.fill = False
ax8.zaxis.pane.fill = False
ax8.xaxis.pane.set_edgecolor('none')
ax8.yaxis.pane.set_edgecolor('none')
ax8.zaxis.pane.set_edgecolor('none')
ax8.grid(color='#D8D8D8', linestyle='-', linewidth=0.6)

ax8.scatter(sc_t[:, 0], sc_t[:, 1], sc_t[:, 2], color='red', marker=(8, 2, 0), s=65,
            linewidth=1.1, depthshade=False, label='Trojan chip')
ax8.scatter(sc_g[:, 0], sc_g[:, 1], sc_g[:, 2], color='blue', facecolors='none', edgecolors='blue',
            marker='o', s=65, linewidth=1.5, depthshade=False, label='Golden chip')
ax8.scatter([center_t_pca[0]], [center_t_pca[1]], [center_t_pca[2]], color='red', facecolors='none',
            edgecolors='red', marker='s', s=120, linewidth=2.2, depthshade=False, label='Trojan clustering center')
ax8.scatter([center_g_pca[0]], [center_g_pca[1]], [center_g_pca[2]], color='blue', facecolors='none',
            edgecolors='blue', marker='s', s=120, linewidth=2.2, depthshade=False, label='Golden clustering center')

ax8.xaxis.set_rotate_label(False)
ax8.yaxis.set_rotate_label(False)
ax8.zaxis.set_rotate_label(False)

ax8.set_xlabel('The first projection', fontweight='bold', fontstyle='italic', fontsize=11, rotation=0, labelpad=16)
ax8.set_ylabel('The second projection', fontweight='bold', fontstyle='italic', fontsize=11, rotation=0, labelpad=18)
ax8.set_zlabel('The third projection', fontweight='bold', fontstyle='italic', fontsize=11, rotation=90, labelpad=10)

for tick in ax8.xaxis.get_ticklabels() + ax8.yaxis.get_ticklabels() + ax8.zaxis.get_ticklabels():
    tick.set_fontweight('bold')
    tick.set_fontstyle('italic')
    tick.set_fontsize(9.5)

ax8.view_init(elev=18, azim=-128)
leg8 = ax8.legend(loc='upper right', edgecolor='black', framealpha=1.0, fancybox=False, fontsize=10)
for text in leg8.get_texts():
    text.set_fontweight('bold')
    text.set_fontstyle('italic')

plt.tight_layout()
fig8_png = SCREENSHOTS_DIR / "fig8_pca_3d_clusters_reproduced.png"
fig8.savefig(fig8_png, dpi=300)
plt.close(fig8)
print(f"[+] Exported Figure 8 to: {fig8_png}")
print("[+] Script 03 completed successfully.")
