# ==============================================================================
# SPECTRA - Master Vivado TCL Automation Script
# Project:     SPECTRA Hardware-Software Co-Simulation Bridge
# Reference:   IEEE Internet of Things Journal 2024 (Chunhua He et al.)
# Target FPGA: Xilinx Artix-7 (xc7a35tcsg324-1)
# Mode:        Batch / GUI Execution without Hardcoded Paths
# ==============================================================================

# 1. Resolve Repository Roots Dynamically
set SCRIPT_DIR [file normalize [file dirname [info script]]]
set REPO_ROOT  [file normalize "$SCRIPT_DIR/.."]
set PROJ_DIR   [file normalize "$REPO_ROOT/vivado_project"]
set PROJ_NAME  "spectra_vivado"
set PART_NAME  "xc7a35tcsg324-1"

puts "======================================================================"
puts "[+] SPECTRA VIVADO HARDWARE CO-SIMULATION & SYNTHESIS FLOW"
puts "======================================================================"
puts "[+] Script Dir : $SCRIPT_DIR"
puts "[+] Repo Root  : $REPO_ROOT"
puts "[+] Proj Dir   : $PROJ_DIR"
puts "[+] Target FPGA: $PART_NAME"
puts "======================================================================"

# Ensure output directories exist
file mkdir "$REPO_ROOT/reports"
file mkdir "$REPO_ROOT/screenshots"
file mkdir "$REPO_ROOT/references/implementation/reports"

# 2. Project Creation & Source Ingestion
if {[file exists $PROJ_DIR]} {
    file delete -force $PROJ_DIR
}
create_project $PROJ_NAME $PROJ_DIR -part $PART_NAME -force

# Add Synthesis Design Sources
add_files -fileset sources_1 [list \
    "$REPO_ROOT/src/aes_128.v" \
    "$REPO_ROOT/src/aes_128_trojan.v" \
]

# Add Simulation Testbench Sources
add_files -fileset sim_1 [list \
    "$REPO_ROOT/src/tb_sidechannel.v" \
]

set_property top aes_128_trojan [current_fileset]
set_property top tb_sidechannel [get_filesets sim_1]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1

# 3. Behavioral Simulation & Hardware CSV Generation
puts "\n[*] Launching Behavioral Simulation (xsim)..."
set_property -name {xsim.simulate.runtime} -value {all} -objects [get_filesets sim_1]
launch_simulation -simset [get_filesets sim_1] -mode behavioral

# Log all top-level waves
if {[info commands add_wave] ne ""} {
    add_wave /tb_sidechannel/*
}

puts "[*] Running simulation until testbench completes (\$finish)..."
run all

# Export waveform screenshot if GUI active
if {[get_param gui.active] == 1 || [get_param gui.test] == 1} {
    catch {
        write_waveform -format png -force "$REPO_ROOT/screenshots/vivado_waveform_simulation.png"
    }
}

# Locate generated CSV files in xsim simulation directory or working directory
set xsim_run_dir [file normalize "$PROJ_DIR/${PROJ_NAME}.sim/sim_1/behav/xsim"]
set csv_candidates [list $xsim_run_dir [pwd] "$REPO_ROOT"]

set golden_csv_found ""
set trojan_csv_found ""

foreach cand $csv_candidates {
    if {[file exists [file join $cand "power_trace_golden.csv"]]} {
        set golden_csv_found [file join $cand "power_trace_golden.csv"]
    }
    if {[file exists [file join $cand "power_trace_trojan.csv"]]} {
        set trojan_csv_found [file join $cand "power_trace_trojan.csv"]
    }
}

if {$golden_csv_found ne "" && $trojan_csv_found ne ""} {
    puts "[+] Found generated CSVs at: $golden_csv_found"
    # Copy to spectra/reports/
    file copy -force $golden_csv_found "$REPO_ROOT/reports/power_trace_golden.csv"
    file copy -force $trojan_csv_found "$REPO_ROOT/reports/power_trace_trojan.csv"
    # Copy to spectra/references/implementation/reports/
    file copy -force $golden_csv_found "$REPO_ROOT/references/implementation/reports/power_trace_golden.csv"
    file copy -force $trojan_csv_found "$REPO_ROOT/references/implementation/reports/power_trace_trojan.csv"
    puts "[+] Successfully copied hardware traces to reports/ directories."
} else {
    puts "[!] Warning: CSVs not found in default paths, checking project files..."
    set found_golden [glob -nocomplain -directory $PROJ_DIR -tails -types f "*power_trace_golden.csv*"]
    if {[llength $found_golden] > 0} {
        puts "[+] Located: $found_golden"
    }
}

close_sim -quiet

# 4. RTL Elaboration & Schematic Export
puts "\n[*] Elaborating RTL design for aes_128_trojan..."
synth_design -rtl -top aes_128_trojan -part $PART_NAME
catch {
    write_schematic -format pdf -force "$REPO_ROOT/screenshots/vivado_schematic_rtl.pdf"
}
close_design -quiet

# 5. Gate-Level Synthesis: Golden Core
puts "\n[*] Synthesizing Golden Core (aes_128)..."
synth_design -top aes_128 -part $PART_NAME -flatten_hierarchy rebuilt
report_utilization -file "$REPO_ROOT/reports/vivado_utilization_golden.txt"
report_power -file "$REPO_ROOT/reports/vivado_power_golden.txt"
report_timing_summary -file "$REPO_ROOT/reports/vivado_timing_golden.txt"
close_design -quiet
puts "[+] Golden core synthesis reports saved to reports/."

# 6. Gate-Level Synthesis: Trojan Core (with DONT_TOUCH preserved)
puts "\n[*] Synthesizing Trojan-Infected Core (aes_128_trojan)..."
synth_design -top aes_128_trojan -part $PART_NAME -flatten_hierarchy rebuilt
report_utilization -file "$REPO_ROOT/reports/vivado_utilization_trojan.txt"
report_power -file "$REPO_ROOT/reports/vivado_power_trojan.txt"
report_timing_summary -file "$REPO_ROOT/reports/vivado_timing_trojan.txt"
close_design -quiet
puts "[+] Trojan core synthesis reports saved to reports/."

puts "\n======================================================================"
puts "[+] VIVADO FULL FLOW EXECUTION FINISHED SUCCESSFULLY!"
puts "======================================================================"
