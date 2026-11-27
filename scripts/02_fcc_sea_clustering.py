#!/usr/bin/env python3
"""
SPECTRA - Script 02: Fuzzy C-Means Clustering (FCC) & Spectral Energy Analysis (SEA)
Reference Conformance: IEEE JIOT 2024 (Eq. 8 - Eq. 10 FCC, Eq. 13 SEA)
"""

import json
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"

print("[+] Executing SPECTRA Script 02: FCC & SEA Unsupervised Clustering...")

with open(REPORTS_DIR / "spectral_eigenvectors.json", "r", encoding="utf-8") as f:
    data = json.load(f)

train_chips = data["training_chips"]
chip_ids = [item["chip_id"] for item in train_chips]
X_train = np.array([item["ev"] for item in train_chips], dtype=np.float64)
raw_energies = np.array([item["raw_energy"] for item in train_chips], dtype=np.float64)
true_labels = np.array([item["label"] for item in train_chips])

N, D = X_train.shape
C = 2
M = 2.0
MAX_ITER = 1000
TOL = 1e-6

np.random.seed(42)
U = np.random.dirichlet(np.ones(C), size=N)

for iteration in range(MAX_ITER):
    U_prev = U.copy()
    Um = U ** M
    V = (Um.T @ X_train) / (np.sum(Um, axis=0)[:, np.newaxis] + 1e-12)

    D_mat = np.zeros((N, C))
    for j in range(C):
        D_mat[:, j] = np.linalg.norm(X_train - V[j], axis=1)
    D_mat = np.maximum(D_mat, 1e-12)

    power_exp = 2.0 / (M - 1.0)
    for j in range(C):
        denom = np.sum((D_mat[:, j:j + 1] / D_mat) ** power_exp, axis=1)
        U[:, j] = 1.0 / (denom + 1e-12)

    if np.max(np.abs(U - U_prev)) < TOL:
        print(f"[+] FCC converged in {iteration+1} iterations.")
        break

# Unsupervised SEA Cluster Labeling (Eq. 13) via raw spectral energy
Um = U ** M
energy_c0 = float(np.sum(Um[:, 0] * raw_energies) / (np.sum(Um[:, 0]) + 1e-12))
energy_c1 = float(np.sum(Um[:, 1] * raw_energies) / (np.sum(Um[:, 1]) + 1e-12))

if energy_c0 >= energy_c1:
    trojan_cluster_idx, golden_cluster_idx = 0, 1
    e_trojan, e_golden = energy_c0, energy_c1
else:
    trojan_cluster_idx, golden_cluster_idx = 1, 0
    e_trojan, e_golden = energy_c1, energy_c0

V_golden = V[golden_cluster_idx]
V_trojan = V[trojan_cluster_idx]

raw_assign = np.argmax(U, axis=1)
pred_binary = (raw_assign == trojan_cluster_idx).astype(int)
accuracy = float(np.mean(pred_binary == true_labels) * 100.0)
print(f"[+] SEA Unsupervised Cluster Labeling Accuracy: {accuracy:.2f}%")

golden_ids = [chip_ids[i] for i in range(N) if pred_binary[i] == 0]
trojan_ids = [chip_ids[i] for i in range(N) if pred_binary[i] == 1]

output_clustering = {
    "num_clusters": C,
    "fuzziness_m": M,
    "converged_iterations": iteration + 1,
    "sea_golden_energy": e_golden,
    "sea_trojan_energy": e_trojan,
    "unsupervised_accuracy_pct": accuracy,
    "golden_cluster_ids": golden_ids,
    "trojan_cluster_ids": trojan_ids,
    "predicted_labels_train": pred_binary.tolist(),
    "center_golden_129d": V_golden.tolist(),
    "center_trojan_129d": V_trojan.tolist(),
}

out_path = REPORTS_DIR / "clustering_results.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output_clustering, f, indent=2)
print(f"[+] Saved clustering results to {out_path}")
