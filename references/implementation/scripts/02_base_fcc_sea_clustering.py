#!/usr/bin/env python3
"""
SPECTRA Base Paper Replication - Script 02: FCC & SEA Clustering
Paper: "A Side-Channel Hardware Trojan Detection Method Based on Fuzzy C-Means Clustering and Fusion Distance Algorithms"
Authors: Chunhua He et al., IEEE Internet of Things Journal, Vol. 11, No. 8, pp. 13927-13937, 15 April 2024.
Section: Section III-B (Eq. 8 - Eq. 13) & Section IV-C
Description:
  Exact implementation of Fuzzy C-Means Clustering (FCC) and Spectral Energy Analysis (SEA).
  Parameters conforming to Eq. 12: c = 2, m = 2.0 (opt1), max_iter = 1000 (opt2), epsilon = 1e-6 (opt3).
  Unsupervised clustering of 48 training chips (24 Golden, 24 Trojan) into EX_G and EX_T.
  SEA determines category type using Eq. 13: Integral |EX_1|^2 >= Integral |EX_2|^2 => Trojan.
  Outputs cluster centers mu_G and mu_T to reports/base_clustering_results.json.
"""

import json
import numpy as np
from pathlib import Path

# Paths
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

# Load training data
if not INPUT_JSON.exists():
    raise FileNotFoundError(f"Input file {INPUT_JSON} not found! Please run 01_base_sfa_extract.py first.")

with open(INPUT_JSON, "r") as f:
    data = json.load(f)

training_chips = data["training_chips"]
n_samples = len(training_chips)
n_features = data["eigenvector_dimension"]

print(f"[*] Loaded {n_samples} training chips with {n_features}-D spectral eigenvectors.")

# Matrix X: 48 x 129
X = np.array([chip["ev"] for chip in training_chips], dtype=np.float64)
chip_ids = [chip["chip_id"] for chip in training_chips]
ground_truth = np.array([chip["ground_truth"] for chip in training_chips])

# FCC Parameters conforming to Eq. 12 & Section III-B:
# [mu, U, objF] = fcm(X, c, [opt1, opt2, opt3, opt4])
C = 2              # Number of clusters: 2 (Golden, Trojan)
M = 2.0            # Fuzziness exponent (opt1): 2.0
MAX_ITER = 1000    # Maximum iterations (opt2): 1000
EPSILON = 1e-6     # Objective function convergence threshold (opt3): 1e-6
DISPLAY = True     # opt4: true

# Initialize fuzzy partition matrix U (C x N) randomly such that columns sum to 1
np.random.seed(42)
U = np.random.uniform(0.1, 0.9, size=(C, n_samples))
U = U / np.sum(U, axis=0, keepdims=True)

obj_history = []
centers = np.zeros((C, n_features), dtype=np.float64)

print("[*] Starting Fuzzy C-Means (FCC) Iteration Loop...")

for it in range(MAX_ITER):
    # Eq. 10: Update cluster centers mu_j
    # mu_j = sum_{k=1}^n (P(omega_j | X_k))^b * X_k / sum_{k=1}^n (P(omega_j | X_k))^b
    U_m = U ** M
    sum_u_m = np.sum(U_m, axis=1, keepdims=True) # shape (C, 1)
    centers = (U_m @ X) / (sum_u_m + 1e-15)       # shape (C, n_features)

    # Compute Euclidean distance from each sample X_k to each center mu_j
    # d_jk = ||X_k - mu_j||_2
    dist = np.zeros((C, n_samples), dtype=np.float64)
    for j in range(C):
        diff = X - centers[j]
        dist[j] = np.linalg.norm(diff, axis=1)

    # Eq. 8: Compute objective function value J_fuz
    dist_sq = dist ** 2
    J_fuz = np.sum(U_m * dist_sq)
    obj_history.append(float(J_fuz))

    if DISPLAY and (it % 10 == 0 or it == 0):
        print(f"    Iteration {it+1:3d}: Objective Function J_fuz = {J_fuz:.8e}")

    # Check convergence threshold (opt3 = 1e-6)
    if it > 0 and abs(obj_history[-1] - obj_history[-2]) < EPSILON:
        print(f"[+] FCC converged at iteration {it+1} (improvement < {EPSILON:.1e}).")
        break

    # Eq. 10: Update fuzzy membership matrix U
    # P(omega_j | X_k) = 1 / sum_{l=1}^c (dist_jk / dist_lk)^(2 / (m - 1))
    dist_safe = np.maximum(dist, 1e-12)
    power = 2.0 / (M - 1.0)
    for j in range(C):
        ratio = dist_safe[j:j+1, :] / dist_safe # shape (C, n_samples)
        U[j] = 1.0 / np.sum(ratio ** power, axis=0)

# Eq. 11: Defuzzification (Maximum posterior probability assignment)
cluster_labels = np.argmax(U, axis=0)

# ==============================================================================
# Spectral Energy Analysis (SEA) - Section III-B, Equation 13
# ==============================================================================
print("[*] Performing Spectral Energy Analysis (SEA) via Equation 13...")

# Total spectral energy integral: sum_{k in cluster} sum_{i=1}^129 |X_k[i]|^2
energy_cluster_0 = np.sum(X[cluster_labels == 0] ** 2)
energy_cluster_1 = np.sum(X[cluster_labels == 1] ** 2)

mean_energy_0 = energy_cluster_0 / max(1, np.sum(cluster_labels == 0))
mean_energy_1 = energy_cluster_1 / max(1, np.sum(cluster_labels == 1))

print(f"    Cluster 0 Total Energy: {energy_cluster_0:.4e} (Mean per chip: {mean_energy_0:.4e})")
print(f"    Cluster 1 Total Energy: {energy_cluster_1:.4e} (Mean per chip: {mean_energy_1:.4e})")

# Eq. 13: Type(EX_1) = Trojan if Integral |EX_1|^2 >= Integral |EX_2|^2, else Golden
if energy_cluster_0 >= energy_cluster_1:
    trojan_cluster_idx = 0
    golden_cluster_idx = 1
else:
    trojan_cluster_idx = 1
    golden_cluster_idx = 0

mu_T = centers[trojan_cluster_idx]
mu_G = centers[golden_cluster_idx]

# Map predictions: 0 for Golden, 1 for Trojan
predicted_labels = np.zeros(n_samples, dtype=int)
predicted_labels[cluster_labels == trojan_cluster_idx] = 1

# Evaluation on training set
correct = np.sum(predicted_labels == ground_truth)
accuracy = (correct / n_samples) * 100.0

ex_g_chips = [chip_ids[i] for i in range(n_samples) if predicted_labels[i] == 0]
ex_t_chips = [chip_ids[i] for i in range(n_samples) if predicted_labels[i] == 1]

print(f"[+] SEA Category Identification Complete:")
print(f"    Golden Cluster: {len(ex_g_chips)} chips, Cluster Center norm = {np.linalg.norm(mu_G):.4f}")
print(f"    Trojan Cluster: {len(ex_t_chips)} chips, Cluster Center norm = {np.linalg.norm(mu_T):.4f}")
print(f"[+] Training Unsupervised Clustering Accuracy: {accuracy:.2f}% ({correct}/{n_samples})")

# Export Clustering Results
clustering_results = {
    "c_clusters": C,
    "fuzziness_m": M,
    "max_iterations": MAX_ITER,
    "tolerance_epsilon": EPSILON,
    "converged_iteration": len(obj_history),
    "final_objective_value": obj_history[-1],
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
            "ground_truth": "Trojan" if ground_truth[i] == 1 else "Golden",
            "membership_golden": float(U[golden_cluster_idx, i]),
            "membership_trojan": float(U[trojan_cluster_idx, i])
        } for i in range(n_samples)
    }
}

with open(OUTPUT_JSON, "w") as f:
    json.dump(clustering_results, f, indent=2)

print(f"[+] Clustering results successfully saved to: {OUTPUT_JSON}")
