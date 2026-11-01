# ==============================================================================
# SPECTRA - Top-Level Vivado TCL Dispatcher
# Invokes the full Vivado co-simulation and synthesis flow for SPECTRA
# ==============================================================================
set SCRIPT_DIR [file normalize [file dirname [info script]]]
source [file join $SCRIPT_DIR "scripts" "run_vivado_full_flow.tcl"]
