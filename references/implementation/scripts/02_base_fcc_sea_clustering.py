#!/usr/bin/env python3
"""
SPECTRA Base Paper Replication - Script 02: FCC & SEA Clustering
Paper: "A Side-Channel Hardware Trojan Detection Method Based on Fuzzy C-Means Clustering and Fusion Distance Algorithms"
Authors: Chunhua He et al., IEEE Internet of Things Journal, Vol. 11, No. 8, pp. 13927-13937, 15 April 2024.
Section: Section III-B (Eq. 8 - Eq. 13) & Section IV-C
Description:
  Purely unsupervised Fuzzy C-Means Clustering (c=2, m=2.0, tol=1e-6) and
  Spectral Energy Analysis (SEA, Eq. 13: Integral |EX_T|^2 > Integral |EX_G|^2).
  Zero ground-truth label usage during clustering or SEA labeling.
"""

import json
from pathlib import Path
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_JSON = REPORTS_DIR / "base_spectral_eigenvectors.json"
OUTPUT_JSON = REPORTS_DIR / "base_clustering_results.json"

print("================================================================================")
print("[+] SPECTRA Base Paper Script 02: Fuzzy C-Means (FCC) & SEA Clustering")
print("    Conformance: Section III-B (Eq. 8 - Eq. 13), Section IV-C")
print("================================================================================")

if not INPUT_JSON.exists():
    raise FileNotFoundError(f"Input file {INPUT_JSON} not found! Run 01_base_sfa_extract.py first.")

with open(INPUT_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

training_chips = data["training_chips"]
n_samples = len(training_chips)
n_features = data["eigenvector_dimension"]

X = np.array([chip["ev"] for chip in training_chips], dtype=np.float64)
X_raw = np.array([chip["ev_raw"] for chip in training_chips], dtype=np.float64)
chip_ids = [chip["chip_id"] for chip in training_chips]
ground_truth = np.array([chip["ground_truth"] for chip in training_chips])

print(f"[*] Loaded {n_samples} training chips with {n_features}-D spectral eigenvectors.")

# Pure Unsupervised FCM (c=2, m=2.0, max_iter=1000, tol=1e-6)
C = 2
M = 2.0
MAX_ITER = 1000
EPSILON = 1e-6

np.random.seed(42)
U = np.random.uniform(0.1, 0.9, size=(C, n_samples))
U = U / np.sum(U, axis=0, keepdims=True)

obj_history = []
centers = np.zeros((C, n_features), dtype=np.float64)

for it in range(MAX_ITER):
    U_prev = U.copy()
    Um = U ** M
    sum_u_m = np.sum(Um, axis=1, keepdims=True)
    centers = (Um @ X) / (sum_u_m + 1e-15)

    dist = np.zeros((C, n_samples), dtype=np.float64)
    for j in range(C):
        dist[j] = np.linalg.norm(X - centers[j], axis=1)

    J_fuz = float(np.sum(Um * (dist ** 2)))
    obj_history.append(J_fuz)

    if it % 10 == 0 or it == 0:
        print(f"    Iteration {it+1:3d}: Objective Function J_fuz = {J_fuz:.8e}")

    dist_safe = np.maximum(dist, 1e-12)
    power = 2.0 / (M - 1.0)
    for j in range(C):
        ratio = dist_safe[j:j+1, :] / dist_safe
        U[j] = 1.0 / np.sum(ratio ** power, axis=0)

    if it > 0 and np.max(np.abs(U - U_prev)) < EPSILON:
        print(f"[+] FCC converged at iteration {it+1} (max |dU| < {EPSILON:.1e}).")
        break

# Defuzzification
cluster_labels = np.argmax(U, axis=0)

# Spectral Energy Analysis (SEA) - Eq. 13 (strictly unsupervised, zero ground-truth labels)
mask_c0 = (cluster_labels == 0)
mask_c1 = (cluster_labels == 1)

energy_cluster_0 = float(np.sum(X_raw[mask_c0] ** 2))
energy_cluster_1 = float(np.sum(X_raw[mask_c1] ** 2))
mean_energy_0 = energy_cluster_0 / max(1, int(np.sum(mask_c0)))
mean_energy_1 = energy_cluster_1 / max(1, int(np.sum(mask_c1)))

print("[*] Spectral Energy Analysis (SEA, Eq. 13):")
print(f"    Cluster 0 Total Energy: {energy_cluster_0:.4e} (Mean/chip: {mean_energy_0:.4e}, N={np.sum(mask_c0)})")
print(f"    Cluster 1 Total Energy: {energy_cluster_1:.4e} (Mean/chip: {mean_energy_1:.4e}, N={np.sum(mask_c1)})")

if mean_energy_0 >= mean_energy_1:
    trojan_cluster_idx = 0
    golden_cluster_idx = 1
else:
    trojan_cluster_idx = 1
    golden_cluster_idx = 0

mu_T = centers[trojan_cluster_idx]
mu_G = centers[golden_cluster_idx]

predicted_labels = (cluster_labels == trojan_cluster_idx).astype(int)
correct = int(np.sum(predicted_labels == ground_truth))
accuracy = (correct / n_samples) * 100.0

ex_g_chips = [chip_ids[i] for i in range(n_samples) if predicted_labels[i] == 0]
ex_t_chips = [chip_ids[i] for i in range(n_samples) if predicted_labels[i] == 1]

print(f"[+] Unsupervised Golden Cluster: {len(ex_g_chips)} chips, ||mu_G|| = {np.linalg.norm(mu_G):.4f}")
print(f"[+] Unsupervised Trojan Cluster: {len(ex_t_chips)} chips, ||mu_T|| = {np.linalg.norm(mu_T):.4f}")
print(f"[+] Training Unsupervised Clustering Accuracy: {accuracy:.2f}% ({correct}/{n_samples})")

clustering_results = {
    "c_clusters": C,
    "fuzziness_m": M,
    "max_iterations": MAX_ITER,
    "tolerance_epsilon": EPSILON,
    "converged_iteration": len(obj_history),
    "final_objective_value": obj_history[-1],
    "mean_energy_golden": float(mean_energy_1 if trojan_cluster_idx == 0 else mean_energy_0),
    "mean_energy_trojan": float(mean_energy_0 if trojan_cluster_idx == 0 else mean_energy_1),
    "clustering_accuracy_percent": accuracy,
    "golden_chips_count": len(ex_g_chips),
    "trojan_chips_count": len(ex_t_chips),
    "golden_cluster_indices": ex_g_chips,
    "trojan_cluster_indices": ex_t_chips,
    "mu_golden": mu_G.tolist(),
    "mu_trojan": mu_T.tolist(),
    "cluster_assignment": {
        chip_ids[i]: {
            "assigned_cluster": "Trojan" if predicted_labels[i] == 1 else "Golden",
            "membership_golden": float(U[golden_cluster_idx, i]),
            "membership_trojan": float(U[trojan_cluster_idx, i])
        } for i in range(n_samples)
    }
}

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(clustering_results, f, indent=2)

print(f"[+] Clustering results saved to: {OUTPUT_JSON}")
