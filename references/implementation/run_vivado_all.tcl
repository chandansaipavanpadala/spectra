# ==============================================================================
# Base Paper - Master Vivado TCL Automation Script
# Project:     Base Paper Replication (Chunhua He et al., IEEE JIOT 2024)
# Target FPGA: Xilinx Artix-7 (xc7a35tcsg324-1)
# Mode:        Batch / GUI Execution without Hardcoded Paths
# ==============================================================================

set SCRIPT_DIR [file normalize [file dirname [info script]]]
set BASE_ROOT  $SCRIPT_DIR
set REPO_ROOT  [file normalize "$BASE_ROOT/../../.."]
set PROJ_DIR   [file normalize "$BASE_ROOT/vivado_project_base"]
set PROJ_NAME  "base_paper_vivado"
set PART_NAME  "xc7a35tcsg324-1"

puts "======================================================================"
puts "[+] BASE PAPER VIVADO CO-SIMULATION & SYNTHESIS FLOW"
puts "======================================================================"
puts "[+] Base Root  : $BASE_ROOT"
puts "[+] Target FPGA: $PART_NAME"
puts "======================================================================"

file mkdir "$BASE_ROOT/reports"
file mkdir "$BASE_ROOT/screenshots"

# Create / Overwrite project
if {[file exists $PROJ_DIR]} {
    file delete -force $PROJ_DIR
}
create_project $PROJ_NAME $PROJ_DIR -part $PART_NAME -force

# Add RTL & TB Sources
add_files -fileset sources_1 [list \
    "$BASE_ROOT/src/aes_128_base.v" \
    "$BASE_ROOT/src/aes_128_trojan_base.v" \
]

add_files -fileset sim_1 [list \
    "$BASE_ROOT/src/tb_sidechannel_base.v" \
]

set_property top aes_128_trojan_base [current_fileset]
set_property top tb_sidechannel_base [get_filesets sim_1]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1

# Launch Behavioral Simulation
puts "\n[*] Launching Behavioral Simulation (xsim)..."
set_property -name {xsim.simulate.runtime} -value {all} -objects [get_filesets sim_1]
launch_simulation -simset [get_filesets sim_1] -mode behavioral

if {[info commands add_wave] ne ""} {
    add_wave /tb_sidechannel_base/*
}

puts "[*] Running simulation until testbench completes (\$finish)..."
run all

# Locate and copy generated CSV files
set xsim_run_dir [file normalize "$PROJ_DIR/${PROJ_NAME}.sim/sim_1/behav/xsim"]
set csv_candidates [list $xsim_run_dir [pwd] "$BASE_ROOT"]

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
    file copy -force $golden_csv_found "$BASE_ROOT/reports/power_trace_golden.csv"
    file copy -force $trojan_csv_found "$BASE_ROOT/reports/power_trace_trojan.csv"
    puts "[+] Successfully copied hardware traces to Base Paper reports/."
}

close_sim -quiet

# Gate-Level Synthesis: Golden Core
puts "\n[*] Synthesizing Base Golden Core (aes_128_base)..."
synth_design -top aes_128_base -part $PART_NAME -flatten_hierarchy rebuilt
report_utilization -file "$BASE_ROOT/reports/vivado_utilization_golden.txt"
report_power -file "$BASE_ROOT/reports/vivado_power_golden.txt"
report_timing_summary -file "$BASE_ROOT/reports/vivado_timing_golden.txt"
close_design -quiet

# Gate-Level Synthesis: Trojan Core
puts "\n[*] Synthesizing Base Trojan Core (aes_128_trojan_base)..."
synth_design -top aes_128_trojan_base -part $PART_NAME -flatten_hierarchy rebuilt
report_utilization -file "$BASE_ROOT/reports/vivado_utilization_trojan.txt"
report_power -file "$BASE_ROOT/reports/vivado_power_trojan.txt"
report_timing_summary -file "$BASE_ROOT/reports/vivado_timing_trojan.txt"
close_design -quiet

puts "\n======================================================================"
puts "[+] BASE PAPER VIVADO FLOW COMPLETED SUCCESSFULLY!"
puts "======================================================================"
