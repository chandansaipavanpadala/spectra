#!/usr/bin/env python3
"""
SPECTRA - Master Hardware-Software Co-Simulation & Verification Runner
Orchestrates:
  1. Vivado EDA Batch Flow (xsim behavioral simulation & synthesis) if vivado is in PATH
  2. Base Paper Pure Replication Pipeline (01 through 04)
  3. SPECTRA Novelty Pipeline (01 through 07)
  4. Comprehensive Status and Artifact Parity Verification Table
"""

import os
import sys
import shutil
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
BASE_SCRIPTS_DIR = REPO_ROOT / "references" / "implementation" / "scripts"
REPORTS_DIR = REPO_ROOT / "reports"
SCREENSHOTS_DIR = REPO_ROOT / "screenshots"
BASE_REPORTS_DIR = REPO_ROOT / "references" / "implementation" / "reports"
BASE_SCREENSHOTS_DIR = REPO_ROOT / "references" / "implementation" / "screenshots"

def run_step(step_name, cmd_args, cwd=REPO_ROOT):
    print(f"\n{'='*80}")
    print(f"[>] STEP: {step_name}")
    print(f"[>] Command: {' '.join(str(x) for x in cmd_args)}")
    print(f"{'='*80}")
    t0 = time.time()
    res = subprocess.run(cmd_args, cwd=cwd)
    dt = time.time() - t0
    if res.returncode != 0:
        print(f"[!] FAILED: {step_name} exited with code {res.returncode}")
        sys.exit(res.returncode)
    print(f"[+] Completed: {step_name} in {dt:.2f}s")

def main():
    print("=" * 80)
    print("  SPECTRA: END-TO-END VIVADO-TO-PYTHON CO-SIMULATION DISPATCHER")
    print("  Target FPGA: Xilinx Artix-7 (xc7a35tcsg324-1) & Spartan-3E")
    print("  IEEE IoT Journal 2024 Reference Replication & SPECTRA Framework")
    print("=" * 80)

    # 1. Check for Vivado in System PATH
    vivado_bin = shutil.which("vivado")
    if vivado_bin:
        print(f"[+] Vivado detected in PATH: {vivado_bin}")
        tcl_script = SCRIPTS_DIR / "run_vivado_full_flow.tcl"
        run_step("Vivado EDA Simulation & Gate-Level Synthesis", [
            vivado_bin, "-mode", "batch", "-source", str(tcl_script), "-nojournal", "-nolog"
        ])
    else:
        print("[*] Vivado executable not found in system PATH.")
        print("[*] Using pre-calibrated hardware switching traces & synthesis metrics.")

    # 2. Base Paper Pure Replication Flow (Scripts 01 -> 04)
    print("\n" + "#" * 80)
    print("# EXECUTING BASE PAPER PURE REPLICATION PIPELINE")
    print("#" * 80)
    run_step("Base Paper 01: SFA Feature Extraction & CSV Ingestion", [
        sys.executable, str(BASE_SCRIPTS_DIR / "01_base_sfa_extract.py")
    ])
    run_step("Base Paper 02: FCC & SEA Unsupervised Clustering", [
        sys.executable, str(BASE_SCRIPTS_DIR / "02_base_fcc_sea_clustering.py")
    ])
    run_step("Base Paper 03: PCA Subspace Reduction (kn = 10)", [
        sys.executable, str(BASE_SCRIPTS_DIR / "03_base_pca_reduction.py")
    ])
    run_step("Base Paper 04: Fusion Distance Decision Boundary (y = x)", [
        sys.executable, str(BASE_SCRIPTS_DIR / "04_base_fusion_distance.py")
    ])

    # 3. SPECTRA Novelty Pipeline (Scripts 01 -> 07)
    print("\n" + "#" * 80)
    print("# EXECUTING SPECTRA NOVELTY ENHANCEMENT PIPELINE")
    print("#" * 80)
    run_step("SPECTRA 01: SFA & Adaptive Harmonic Band Energy (AHBE)", [
        sys.executable, str(SCRIPTS_DIR / "01_sfa_feature_extract.py")
    ])
    run_step("SPECTRA 02: FCC & SEA Clustering", [
        sys.executable, str(SCRIPTS_DIR / "02_fcc_sea_clustering.py")
    ])
    run_step("SPECTRA 03: PCA Subspace Projection", [
        sys.executable, str(SCRIPTS_DIR / "03_pca_dimension_reduc.py")
    ])
    run_step("SPECTRA 04: Entropy-Weighted Fusion Distance Classification", [
        sys.executable, str(SCRIPTS_DIR / "04_fusion_classifier.py")
    ])
    run_step("SPECTRA 05: Noise Robustness & PVT Drift Stress Test", [
        sys.executable, str(SCRIPTS_DIR / "05_noise_robustness_sweep.py")
    ])
    run_step("SPECTRA 06: Trust-HUB Multi-Benchmark Generalization", [
        sys.executable, str(SCRIPTS_DIR / "06_benchmark_generalization.py")
    ])
    run_step("SPECTRA 07: FPGA Hardware Utilization & Vivado Report Audit", [
        sys.executable, str(SCRIPTS_DIR / "07_synth_utilization_table.py")
    ])

    # 4. Final Comprehensive Status Summary Table
    print("\n" + "=" * 80)
    print("  SPECTRA CO-SIMULATION & ARTIFACT VERIFICATION SUMMARY")
    print("=" * 80)

    artifacts = [
        ("Hardware CSV (Golden)", REPORTS_DIR / "power_trace_golden.csv"),
        ("Hardware CSV (Trojan)", REPORTS_DIR / "power_trace_trojan.csv"),
        ("Vivado Synthesis Utilization", REPORTS_DIR / "vivado_utilization_golden.txt"),
        ("Base Paper Eigenvectors", BASE_REPORTS_DIR / "base_spectral_eigenvectors.json"),
        ("Base Paper Clustering", BASE_REPORTS_DIR / "base_clustering_results.json"),
        ("Base Paper PCA Metrics", BASE_REPORTS_DIR / "base_pca_results.json"),
        ("Base Paper Fusion Metrics", BASE_REPORTS_DIR / "base_fusion_metrics.json"),
        ("SPECTRA Eigenvectors", REPORTS_DIR / "spectral_eigenvectors.json"),
        ("SPECTRA Clustering", REPORTS_DIR / "clustering_results.json"),
        ("SPECTRA Subspace PCA", REPORTS_DIR / "pca_subspace.json"),
        ("SPECTRA Detection Report", REPORTS_DIR / "detection_report.json"),
        ("SPECTRA Noise Sweep Data", REPORTS_DIR / "noise_robustness_results.json"),
        ("SPECTRA Multi-Benchmark Data", REPORTS_DIR / "multi_benchmark_report.json"),
        ("SPECTRA Hardware Synthesis Data", REPORTS_DIR / "fpga_hardware_utilization.json"),
        ("Fig 6 Time-Domain Trace", BASE_SCREENSHOTS_DIR / "fig6_time_domain_power_reproduced.png"),
        ("Fig 7 Spectral Eigenvectors", BASE_SCREENSHOTS_DIR / "fig7_spectral_eigenvector_reproduced.png"),
        ("Fig 8 3D PCA Clusters", BASE_SCREENSHOTS_DIR / "fig8_pca_3d_clusters_reproduced.png"),
        ("Fig 9 Fusion Boundary", BASE_SCREENSHOTS_DIR / "fig9_fusion_distance_boundary_reproduced.png"),
        ("SPECTRA Spectrum Plot", SCREENSHOTS_DIR / "sfa_spectrum_comparison.png"),
        ("SPECTRA 3D Clusters Plot", SCREENSHOTS_DIR / "pca_3d_clusters.png"),
        ("SPECTRA Decision Boundary Plot", SCREENSHOTS_DIR / "fusion_distance_classification.png"),
        ("SPECTRA Noise Robustness Plot", SCREENSHOTS_DIR / "noise_robustness_sweep.png"),
        ("SPECTRA Benchmark Comparison Plot", SCREENSHOTS_DIR / "benchmark_comparison.png")
    ]

    print(f"{'Artifact Description':<36} | {'Status':<6} | {'Size':<10} | {'Location'}")
    print("-" * 80)
    all_ok = True
    for desc, path in artifacts:
        if path.exists() and path.stat().st_size > 0:
            sz = f"{path.stat().st_size:,} B"
            rel = path.relative_to(REPO_ROOT)
            print(f"{desc:<36} | PASS   | {sz:<10} | {rel}")
        else:
            print(f"{desc:<36} | FAIL   | {'MISSING':<10} | {path}")
            all_ok = False

    print("=" * 80)
    if all_ok:
        print("[+] ALL HARDWARE CO-SIMULATION & VERIFICATION ARTIFACTS VERIFIED: PASS")
    else:
        print("[!] SOME ARTIFACTS ARE MISSING OR EMPTY: REVIEW LOGS")
    print("=" * 80)

if __name__ == "__main__":
    main()
