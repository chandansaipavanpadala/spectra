# ==============================================================================
# Base Paper - Vivado Scripts Dispatcher
# Delegates to references/implementation/run_vivado_all.tcl
# ==============================================================================
set SCRIPT_DIR [file normalize [file dirname [info script]]]
source [file normalize "$SCRIPT_DIR/../run_vivado_all.tcl"]
