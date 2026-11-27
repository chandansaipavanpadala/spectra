#!/usr/bin/env python3
"""
SPECTRA - Script 01: Spectral Feature Analysis (SFA) & AHBE Feature Extraction
Reference Conformance: IEEE JIOT 2024 (Eq. 1 - Eq. 3)
Novel Enhancement: Adaptive Harmonic Band Energy (AHBE) Integration
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

from spectra_signal_core import (
    FS, F_CLK_NOM, N_SAMPLES,
    load_vivado_csv_traces,
    synthesize_trace_from_vivado_csv,
    extract_ev_ahbe,
)

REPO_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = REPO_ROOT / "reports"
SCREENSHOTS_DIR = REPO_ROOT / "screenshots"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

N_CHIPS_TRAIN_GOLDEN = 24
N_CHIPS_TRAIN_TROJAN = 24
N_CHIPS_VAL_GOLDEN = 12
N_CHIPS_VAL_TROJAN = 12

print("================================================================================")
print("[+] Executing SPECTRA Script 01: SFA & AHBE Feature Extraction...")
print("================================================================================")

tog_g, vcc_g, tog_t, vcc_t = load_vivado_csv_traces(
    REPORTS_DIR / "power_trace_golden.csv",
    REPORTS_DIR / "power_trace_trojan.csv",
)

mean_g = float(np.mean(tog_g))
mean_t = float(np.mean(tog_t))
delta_pct = ((mean_t - mean_g) / (mean_g + 1e-12)) * 100.0
print(f"[+] Ingested Vivado CSV Traces: {len(tog_g)} cycles @ {F_CLK_NOM/1e6:.1f} MHz")
print(f"[+] Golden Mean Toggle: {mean_g:.3f} bits/cycle | Trojan Mean Toggle: {mean_t:.3f} bits/cycle ({delta_pct:+.2f}%)")

training_data = []
validation_data = []
sample_trace_g = None
sample_trace_t = None
sample_spec_g = None
sample_spec_t = None

# 48 Training Chips (24 Golden, 24 Trojan) with 6% PVT & 25 dB SNR
for i in range(N_CHIPS_TRAIN_GOLDEN):
    tr = synthesize_trace_from_vivado_csv(vcc_g, tog_g, is_trojan=False, chip_seed=i, snr_db=25.0, clk_drift_pct=0.2)
    ev, _, raw_e, pos_spec = extract_ev_ahbe(tr)
    if i == 0:
        sample_trace_g, sample_spec_g = tr, pos_spec
    training_data.append({"chip_id": f"G_train_{i+1}", "label": 0, "raw_energy": raw_e, "ev": ev.tolist()})

for i in range(N_CHIPS_TRAIN_TROJAN):
    tr = synthesize_trace_from_vivado_csv(
        vcc_g, tog_g, vcc_t_cycles=vcc_t, tog_t_cycles=tog_t,
        is_trojan=True, chip_seed=i + 50, snr_db=25.0, clk_drift_pct=0.2
    )
    ev, _, raw_e, pos_spec = extract_ev_ahbe(tr)
    if i == 0:
        sample_trace_t, sample_spec_t = tr, pos_spec
    training_data.append({"chip_id": f"T_train_{i+1}", "label": 1, "raw_energy": raw_e, "ev": ev.tolist()})

# 24 Validation Chips (12 Golden, 12 Trojan)
for i in range(N_CHIPS_VAL_GOLDEN):
    tr = synthesize_trace_from_vivado_csv(vcc_g, tog_g, is_trojan=False, chip_seed=i + 100, snr_db=25.0, clk_drift_pct=0.2)
    ev, _, raw_e, _ = extract_ev_ahbe(tr)
    validation_data.append({"chip_id": f"G_val_{i+1}", "label": 0, "raw_energy": raw_e, "ev": ev.tolist()})

for i in range(N_CHIPS_VAL_TROJAN):
    tr = synthesize_trace_from_vivado_csv(
        vcc_g, tog_g, vcc_t_cycles=vcc_t, tog_t_cycles=tog_t,
        is_trojan=True, chip_seed=i + 150, snr_db=25.0, clk_drift_pct=0.2
    )
    ev, _, raw_e, _ = extract_ev_ahbe(tr)
    validation_data.append({"chip_id": f"T_val_{i+1}", "label": 1, "raw_energy": raw_e, "ev": ev.tolist()})

output_json = {
    "sampling_frequency_hz": FS,
    "clock_frequency_hz": F_CLK_NOM,
    "n_samples": N_SAMPLES,
    "eigenvector_dimension": 129,
    "training_chips": training_data,
    "validation_chips": validation_data,
}

out_path = REPORTS_DIR / "spectral_eigenvectors.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output_json, f, indent=2)
print(f"[+] Saved spectral eigenvectors to {out_path}")

# Plot 1: Time-Domain Traces Comparison (clean formatting, zero raw LaTeX typos)
n_zoom = 2500  # First 10 clock cycles (1.0 us)
t_us = np.arange(n_zoom) / FS * 1e6
plt.figure(figsize=(10, 5), dpi=300)
plt.plot(t_us, sample_trace_g[:n_zoom] * 1e3, label="Golden Chip Shunt Trace (128-bit AES)", color="#007791", alpha=0.88, linewidth=1.2)
plt.plot(t_us, sample_trace_t[:n_zoom] * 1e3, label="Trojan Chip Shunt Trace (2-Bit Counter)", color="#C0392B", alpha=0.72, linewidth=1.1)
plt.title("SPECTRA: Time-Domain Vccint Shunt Power Proxy Traces", fontsize=12, fontweight='bold', pad=12)
plt.xlabel("Time (us)", fontsize=10, fontweight='bold')
plt.ylabel("Shunt Voltage Drop (mV)", fontsize=10, fontweight='bold')
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend(loc="upper right", frameon=True)
plt.tight_layout()
td_path = SCREENSHOTS_DIR / "time_domain_traces.png"
plt.savefig(td_path, dpi=300)
plt.close()
print(f"[+] Saved time-domain traces plot to {td_path}")

# Plot 2: SFA Spectrum Comparison (0 - 250 MHz Zoom)
freq_mhz = np.linspace(0, FS / 2.0, len(sample_spec_g)) / 1e6
zoom_bins = 100000
plt.figure(figsize=(10, 5), dpi=300)
plt.plot(freq_mhz[:zoom_bins], sample_spec_g[:zoom_bins], label="Golden Chip Spectrum (128-bit AES)", color="#007791", alpha=0.85, linewidth=1.2)
plt.plot(freq_mhz[:zoom_bins], sample_spec_t[:zoom_bins], label="Trojan Chip Spectrum (2-Bit Counter Payload)", color="#C0392B", alpha=0.75, linewidth=1.2)
plt.title("SPECTRA: Side-Channel Spectral Feature Analysis (0 - 250 MHz Zoom)", fontsize=12, fontweight='bold', pad=12)
plt.xlabel("Frequency (MHz)", fontsize=10, fontweight='bold')
plt.ylabel("Spectral Magnitude |D(f)|", fontsize=10, fontweight='bold')
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend(loc="upper right", frameon=True)
plt.tight_layout()
spec_path = SCREENSHOTS_DIR / "sfa_spectrum_comparison.png"
plt.savefig(spec_path, dpi=300)
plt.close()
print(f"[+] Saved spectrum comparison figure to {spec_path}")
