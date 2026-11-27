# ==============================================================================
# Base Paper - Master Vivado TCL Automation Script
# Project:     Base Paper Replication (Chunhua He et al., IEEE JIOT 2024)
# Target FPGA: Xilinx Artix-7 (xc7a35tcsg324-1)
# Mode:        Out-of-Context Synthesis & Behavioral Co-Simulation
# ==============================================================================

set SCRIPT_DIR [file normalize [file dirname [info script]]]
set BASE_ROOT  $SCRIPT_DIR
set REPO_ROOT  [file normalize "$BASE_ROOT/../.."]
set PART_NAME  "xc7a35tcsg324-1"
set PROJ_NAME  "base_paper_vivado"

if {[file isdirectory "D:/"]} {
    set PROJ_DIR [file normalize "D:/spectra_vivado/vivado_project_base"]
} elseif {[info exists ::env(LOCALAPPDATA)]} {
    set PROJ_DIR [file normalize "$::env(LOCALAPPDATA)/spectra_vivado/vivado_project_base"]
} else {
    set PROJ_DIR [file normalize "$BASE_ROOT/vivado_project_base"]
}

puts "======================================================================"
puts "\[+\] BASE PAPER VIVADO CO-SIMULATION & OOC SYNTHESIS FLOW"
puts "======================================================================"
puts "\[+\] Base Root  : $BASE_ROOT"
puts "\[+\] Proj Dir   : $PROJ_DIR"
puts "\[+\] Target FPGA: $PART_NAME"
puts "======================================================================"

file mkdir "$BASE_ROOT/reports"
file mkdir "$BASE_ROOT/screenshots"
file mkdir "$REPO_ROOT/reports"

if {[file exists $PROJ_DIR]} {
    catch { file delete -force $PROJ_DIR }
}
create_project $PROJ_NAME $PROJ_DIR -part $PART_NAME -force

add_files -fileset sources_1 [list \
    "$BASE_ROOT/src/aes_128_base.v" \
    "$BASE_ROOT/src/aes_128_trojan_base.v" \
]

add_files -fileset sim_1 [list \
    "$BASE_ROOT/src/tb_sidechannel_base.v" \
]

set_property top aes_128_base [current_fileset]
set_property top tb_sidechannel_base [get_filesets sim_1]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1

puts "\n\[*\] Launching Behavioral Simulation (xsim)..."
set_property -name {xsim.simulate.runtime} -value {all} -objects [get_filesets sim_1]
launch_simulation -simset [get_filesets sim_1] -mode behavioral

if {[info commands add_wave] ne ""} {
    catch { add_wave /tb_sidechannel_base/* }
}

puts "\[*\] Running simulation until testbench completes (\$finish)..."
run all

set xsim_run_dir [file normalize "$PROJ_DIR/${PROJ_NAME}.sim/sim_1/behav/xsim"]
set csv_candidates [list $xsim_run_dir [pwd] "$BASE_ROOT" "$PROJ_DIR"]

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

if {$golden_csv_found eq "" || ![file exists $golden_csv_found] || [file size $golden_csv_found] < 1024} {
    error "FATAL ERROR: power_trace_golden.csv is missing or empty (< 1 KB) after xsim!"
}
if {$trojan_csv_found eq "" || ![file exists $trojan_csv_found] || [file size $trojan_csv_found] < 1024} {
    error "FATAL ERROR: power_trace_trojan.csv is missing or empty (< 1 KB) after xsim!"
}

puts "\[+\] Verified generated CSVs ([file size $golden_csv_found] B / [file size $trojan_csv_found] B)"
file copy -force $golden_csv_found "$BASE_ROOT/reports/power_trace_golden.csv"
file copy -force $trojan_csv_found "$BASE_ROOT/reports/power_trace_trojan.csv"
file copy -force $golden_csv_found "$REPO_ROOT/reports/power_trace_golden.csv"
file copy -force $trojan_csv_found "$REPO_ROOT/reports/power_trace_trojan.csv"
puts "\[+\] Synced hardware CSVs to Base Paper & top-level reports/."

close_sim -quiet

# Out-of-Context Gate-Level Synthesis: Golden Core (aes_128_base)
puts "\n\[*\] Synthesizing Base Golden Core (aes_128_base) in Out-of-Context mode..."
set_property top aes_128_base [current_fileset]
update_compile_order -fileset sources_1
synth_design -mode out_of_context -top aes_128_base -part $PART_NAME
create_clock -period 100.000 -name clk [get_ports clk]
report_utilization    -file "$BASE_ROOT/reports/vivado_utilization_golden.txt"
report_power          -file "$BASE_ROOT/reports/vivado_power_golden.txt"
report_timing_summary -file "$BASE_ROOT/reports/vivado_timing_golden.txt"
close_design -quiet

file copy -force "$BASE_ROOT/reports/vivado_utilization_golden.txt" "$REPO_ROOT/reports/vivado_utilization_golden.txt"
file copy -force "$BASE_ROOT/reports/vivado_power_golden.txt"       "$REPO_ROOT/reports/vivado_power_golden.txt"
file copy -force "$BASE_ROOT/reports/vivado_timing_golden.txt"      "$REPO_ROOT/reports/vivado_timing_golden.txt"

# Out-of-Context Gate-Level Synthesis: Trojan Core (aes_128_trojan_base)
puts "\n\[*\] Synthesizing Base Trojan Core (aes_128_trojan_base) in Out-of-Context mode..."
set_property top aes_128_trojan_base [current_fileset]
update_compile_order -fileset sources_1
synth_design -mode out_of_context -top aes_128_trojan_base -part $PART_NAME
create_clock -period 100.000 -name clk [get_ports clk]
report_utilization    -file "$BASE_ROOT/reports/vivado_utilization_trojan.txt"
report_power          -file "$BASE_ROOT/reports/vivado_power_trojan.txt"
report_timing_summary -file "$BASE_ROOT/reports/vivado_timing_trojan.txt"
close_design -quiet

file copy -force "$BASE_ROOT/reports/vivado_utilization_trojan.txt" "$REPO_ROOT/reports/vivado_utilization_trojan.txt"
file copy -force "$BASE_ROOT/reports/vivado_power_trojan.txt"       "$REPO_ROOT/reports/vivado_power_trojan.txt"
file copy -force "$BASE_ROOT/reports/vivado_timing_trojan.txt"      "$REPO_ROOT/reports/vivado_timing_trojan.txt"

puts "\n======================================================================"
puts "\[+\] BASE PAPER VIVADO FLOW COMPLETED SUCCESSFULLY!"
puts "======================================================================"
exit
