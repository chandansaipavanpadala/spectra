#!/usr/bin/env python3
"""
SPECTRA - Script 03: Principal Component Analysis (PCA) Dimension Reduction
Reference Conformance: IEEE JIOT 2024 (Eq. 14 - Eq. 16: 10-D Subspace Projection, >85% Variance)
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg') # Headless Matplotlib execution
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
SCREENSHOTS_DIR = REPO_ROOT / "screenshots"

print("[+] Executing SPECTRA Script 03: PCA Subspace Projection...")

# Load spectral eigenvectors
with open(REPORTS_DIR / "spectral_eigenvectors.json", "r") as f:
    spec_data = json.load(f)

train_chips = spec_data["training_chips"]
X_train = np.array([item["ev"] for item in train_chips]) # (48, 129)
y_train = np.array([item["label"] for item in train_chips])

# Mean-center the dataset
X_mean = np.mean(X_train, axis=0)
X_centered = X_train - X_mean

# Compute Covariance Matrix and Eigen-decomposition
cov_matrix = np.cov(X_centered, rowvar=False) # (129, 129)
eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)

# Sort eigenvalues and eigenvectors in descending order
sorted_indices = np.argsort(eigenvalues)[::-1]
eigenvalues = eigenvalues[sorted_indices]
eigenvectors = eigenvectors[:, sorted_indices]

# Select top k_n = 10 components (Eq. 14 - Eq. 16, >85% variance explained)
K_COMPONENTS = 10
coeff = eigenvectors[:, :K_COMPONENTS] # Projection Matrix (129, 10)

explained_variance_ratio = np.cumsum(eigenvalues[:K_COMPONENTS]) / np.sum(eigenvalues) * 100.0
print(f"[+] Top {K_COMPONENTS} PCA Components Explained Cumulative Variance: {explained_variance_ratio[-1]:.2f}%")

# Project 129-D training chips into 10-D eigen-subspace (48 x 10)
scores_train = X_centered @ coeff

sc_g = scores_train[y_train == 0] # Golden score matrix (24 x 10)
sc_t = scores_train[y_train == 1] # Trojan score matrix (24 x 10)

# Save PCA subspace results to reports/pca_subspace.json
output_pca = {
    "num_components": K_COMPONENTS,
    "explained_variance_pct": float(explained_variance_ratio[-1]),
    "x_mean_129d": X_mean.tolist(),
    "coeff_matrix_129x10": coeff.tolist(),
    "sc_g_24x10": sc_g.tolist(),
    "sc_t_24x10": sc_t.tolist()
}

with open(REPORTS_DIR / "pca_subspace.json", "w") as f:
    json.dump(output_pca, f, indent=2)

print(f"[+] Saved PCA subspace configuration to {REPORTS_DIR / 'pca_subspace.json'}")

# Generate 3D Scatter Visualization (PC1 vs PC2 vs PC3)
fig = plt.figure(figsize=(9, 7), dpi=300)
ax = fig.add_subplot(111, projection='3d')

ax.scatter(sc_g[:, 0], sc_g[:, 1], sc_g[:, 2], c='#007791', marker='o', s=60, alpha=0.9, label='Golden Chips (24)')
ax.scatter(sc_t[:, 0], sc_t[:, 1], sc_t[:, 2], c='#C0392B', marker='^', s=70, alpha=0.9, label='Trojan Chips (24)')

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
