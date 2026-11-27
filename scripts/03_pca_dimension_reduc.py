#!/usr/bin/env python3
"""
SPECTRA - Script 03: Principal Component Analysis (PCA) Dimension Reduction
Reference Conformance: IEEE JIOT 2024 (Eq. 14 - Eq. 16: 10-D Subspace Projection, >85% Variance)
Strictly unsupervised: splits sc_g and sc_t using Script 02 cluster predictions (NO label leak).
"""

import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
SCREENSHOTS_DIR = REPO_ROOT / "screenshots"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

print("[+] Executing SPECTRA Script 03: PCA Subspace Projection...")

with open(REPORTS_DIR / "spectral_eigenvectors.json", "r", encoding="utf-8") as f:
    spec_data = json.load(f)
with open(REPORTS_DIR / "clustering_results.json", "r", encoding="utf-8") as f:
    cluster_data = json.load(f)

train_chips = spec_data["training_chips"]
X_train = np.array([item["ev"] for item in train_chips], dtype=np.float64)
cluster_pred = np.array(cluster_data["predicted_labels_train"], dtype=int)

X_mean = np.mean(X_train, axis=0)
X_centered = X_train - X_mean

cov_matrix = np.cov(X_centered, rowvar=False)
eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
sorted_indices = np.argsort(eigenvalues)[::-1]
eigenvalues = eigenvalues[sorted_indices]
eigenvectors = eigenvectors[:, sorted_indices]

K_COMPONENTS = 10
coeff = eigenvectors[:, :K_COMPONENTS]
explained_variance_ratio = np.cumsum(eigenvalues[:K_COMPONENTS]) / (np.sum(eigenvalues) + 1e-12) * 100.0
print(f"[+] Top {K_COMPONENTS} PCA Components Explained Cumulative Variance: {explained_variance_ratio[-1]:.2f}%")

scores_train = X_centered @ coeff
# Split scores purely using unsupervised FCM+SEA cluster assignments
sc_g = scores_train[cluster_pred == 0]
sc_t = scores_train[cluster_pred == 1]

output_pca = {
    "num_components": K_COMPONENTS,
    "explained_variance_pct": float(explained_variance_ratio[-1]),
    "x_mean_129d": X_mean.tolist(),
    "coeff_matrix_129x10": coeff.tolist(),
    "sc_g_cluster": sc_g.tolist(),
    "sc_t_cluster": sc_t.tolist(),
}

out_path = REPORTS_DIR / "pca_subspace.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output_pca, f, indent=2)
print(f"[+] Saved PCA subspace configuration to {out_path}")

fig = plt.figure(figsize=(9, 7), dpi=300)
ax = fig.add_subplot(111, projection='3d')
ax.scatter(sc_g[:, 0], sc_g[:, 1], sc_g[:, 2], c='#007791', marker='o', s=60, alpha=0.9, label=f'Golden Cluster ({len(sc_g)})')
ax.scatter(sc_t[:, 0], sc_t[:, 1], sc_t[:, 2], c='#C0392B', marker='^', s=70, alpha=0.9, label=f'Trojan Cluster ({len(sc_t)})')
ax.set_title("SPECTRA: 3D PCA Eigen-Subspace Projection (PC1, PC2, PC3)", fontsize=11, fontweight='bold', pad=12)
ax.set_xlabel("Principal Component 1", fontsize=9, fontweight='bold')
ax.set_ylabel("Principal Component 2", fontsize=9, fontweight='bold')
ax.set_zlabel("Principal Component 3", fontsize=9, fontweight='bold')
ax.legend(loc="upper right", frameon=True)
plt.tight_layout()

screenshot_path = SCREENSHOTS_DIR / "pca_3d_clusters.png"
plt.savefig(screenshot_path, dpi=300)
plt.close()
print(f"[+] Saved 3D PCA cluster visualization to {screenshot_path}")
