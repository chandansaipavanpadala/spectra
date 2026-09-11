#!/usr/bin/env python3
"""
SPECTRA - Script 02: Fuzzy C-Means Clustering (FCC) & Spectral Energy Analysis (SEA)
Reference Conformance: IEEE JIOT 2024 (Eq. 8 - Eq. 10 FCC, Eq. 13 SEA)
"""

import json
import numpy as np
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"

print("[+] Executing SPECTRA Script 02: FCC & SEA Unsupervised Clustering...")

# Load spectral eigenvectors from reports/spectral_eigenvectors.json
input_json_path = REPORTS_DIR / "spectral_eigenvectors.json"
with open(input_json_path, "r") as f:
    data = json.load(f)

train_chips = data["training_chips"]
X_train = np.array([item["ev"] for item in train_chips]) # (48, 129)
true_labels = np.array([item["label"] for item in train_chips])

N, D = X_train.shape
C = 2       # c=2 clusters
M = 2.0     # Fuzziness weighting exponent m=2.0 (Eq. 8)
MAX_ITER = 1000
TOL = 1e-6

np.random.seed(42)

# Step 1: Initialize Membership Matrix U (N x C) randomly such that sum_j U_ij = 1
U = np.random.dirichlet(np.ones(C), size=N)

# Fuzzy C-Means Iterative Optimization (Eq. 8 - Eq. 10)
for iteration in range(MAX_ITER):
    U_prev = U.copy()

    # Eq. 9: Update Cluster Centers V (C x D)
    # V_j = sum_i (u_ij^m * X_i) / sum_i (u_ij^m)
    Um = U ** M
    V = (Um.T @ X_train) / (np.sum(Um, axis=0)[:, np.newaxis] + 1e-12)

    # Calculate Euclidean distances to cluster centers
    # Distances matrix D_mat (N x C)
    D_mat = np.zeros((N, C))
    for j in range(C):
        D_mat[:, j] = np.linalg.norm(X_train - V[j], axis=1)

    # Prevent division by zero
    D_mat = np.maximum(D_mat, 1e-12)

    # Eq. 10: Update Membership Matrix U
    # u_ij = 1 / sum_k=1^c (d_ij / d_ik)^(2/(m-1))
    power_exp = 2.0 / (M - 1.0)
    for j in range(C):
        denom = np.sum((D_mat[:, j:j+1] / D_mat) ** power_exp, axis=1)
        U[:, j] = 1.0 / (denom + 1e-12)

    # Check for convergence
    if np.max(np.abs(U - U_prev)) < TOL:
        print(f"[+] FCC converged in {iteration+1} iterations.")
        break

# Step 2: Spectral Energy Analysis (SEA) Cluster Labeling (Eq. 13)
# Type(EX_1) = Trojan if int(|EX_1|) >= int(|EX_2|), else Golden
energy_c0 = np.sum(V[0] ** 2)
energy_c1 = np.sum(V[1] ** 2)

if energy_c0 >= energy_c1:
    trojan_cluster_idx = 0
    golden_cluster_idx = 1
else:
    trojan_cluster_idx = 1
    golden_cluster_idx = 0

V_golden = V[golden_cluster_idx]
V_trojan = V[trojan_cluster_idx]

# Assign predicted cluster labels
pred_labels = np.argmax(U, axis=1)
if trojan_cluster_idx == 0:
    pred_binary = pred_labels # 0 = Trojan, 1 = Golden -> invert to 0 = Golden, 1 = Trojan
    pred_binary = 1 - pred_binary
else:
    pred_binary = pred_labels

accuracy = np.mean(pred_binary == true_labels) * 100.0
print(f"[+] SEA Unsupervised Cluster Labeling Accuracy: {accuracy:.2f}%")

# Save clustering results to reports/clustering_results.json
output_clustering = {
    "num_clusters": C,
    "fuzziness_m": M,
    "converged_iterations": iteration + 1,
    "sea_golden_energy": float(np.sum(V_golden ** 2)),
    "sea_trojan_energy": float(np.sum(V_trojan ** 2)),
    "unsupervised_accuracy_pct": float(accuracy),
    "center_golden_129d": V_golden.tolist(),
    "center_trojan_129d": V_trojan.tolist()
}

with open(REPORTS_DIR / "clustering_results.json", "w") as f:
    json.dump(output_clustering, f, indent=2)

print(f"[+] Saved clustering results to {REPORTS_DIR / 'clustering_results.json'}")
