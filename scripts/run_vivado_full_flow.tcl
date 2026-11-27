# ==============================================================================
# SPECTRA - Master Vivado TCL Automation Script
# Project:     SPECTRA Hardware-Software Co-Simulation Bridge
# Reference:   IEEE Internet of Things Journal 2024 (Chunhua He et al.)
# Target FPGA: Xilinx Artix-7 (xc7a35tcsg324-1)
# Mode:        Out-of-Context Synthesis & Behavioral Co-Simulation
# ==============================================================================

set SCRIPT_DIR [file normalize [file dirname [info script]]]
set REPO_ROOT  [file normalize "$SCRIPT_DIR/.."]
set BASE_REPS  [file normalize "$REPO_ROOT/references/implementation/reports"]
set PART_NAME  "xc7a35tcsg324-1"
set PROJ_NAME  "spectra_vivado"

if {[file isdirectory "D:/"]} {
    set PROJ_DIR [file normalize "D:/spectra_vivado/vivado_project"]
} elseif {[info exists ::env(LOCALAPPDATA)]} {
    set PROJ_DIR [file normalize "$::env(LOCALAPPDATA)/spectra_vivado/vivado_project"]
} else {
    set PROJ_DIR [file normalize "$REPO_ROOT/vivado_project"]
}

puts "======================================================================"
puts "\[+\] SPECTRA VIVADO HARDWARE CO-SIMULATION & OOC SYNTHESIS FLOW"
puts "======================================================================"
puts "\[+\] Script Dir : $SCRIPT_DIR"
puts "\[+\] Repo Root  : $REPO_ROOT"
puts "\[+\] Proj Dir   : $PROJ_DIR"
puts "\[+\] Target FPGA: $PART_NAME"
puts "======================================================================"

file mkdir "$REPO_ROOT/reports"
file mkdir "$REPO_ROOT/screenshots"
file mkdir "$BASE_REPS"

# 1. Clean Project Creation & Source Ingestion
if {[file exists $PROJ_DIR]} {
    catch { file delete -force $PROJ_DIR }
}
create_project $PROJ_NAME $PROJ_DIR -part $PART_NAME -force

add_files -fileset sources_1 [list \
    "$REPO_ROOT/src/aes_128.v" \
    "$REPO_ROOT/src/aes_128_trojan.v" \
]

add_files -fileset sim_1 [list \
    "$REPO_ROOT/src/tb_sidechannel.v" \
]

set_property top aes_128_trojan [current_fileset]
set_property top tb_sidechannel [get_filesets sim_1]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1

# 2. Behavioral Simulation & Deterministic CSV Generation
puts "\n\[*\] Launching Behavioral Simulation (xsim)..."
set_property -name {xsim.simulate.runtime} -value {all} -objects [get_filesets sim_1]
launch_simulation -simset [get_filesets sim_1] -mode behavioral

if {[info commands add_wave] ne ""} {
    catch { add_wave /tb_sidechannel/* }
}

puts "\[*\] Running simulation until testbench completes (\$finish)..."
run all

catch {
    write_waveform -format png -force "$REPO_ROOT/screenshots/vivado_waveform_simulation.png"
}

# Locate generated CSV traces
set xsim_run_dir [file normalize "$PROJ_DIR/${PROJ_NAME}.sim/sim_1/behav/xsim"]
set csv_candidates [list $xsim_run_dir [pwd] "$REPO_ROOT" "$PROJ_DIR"]

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

# Fail loudly if CSVs are missing or smaller than 1 KB
if {$golden_csv_found eq "" || ![file exists $golden_csv_found] || [file size $golden_csv_found] < 1024} {
    error "FATAL ERROR: power_trace_golden.csv is missing or empty (< 1 KB) after xsim!"
}
if {$trojan_csv_found eq "" || ![file exists $trojan_csv_found] || [file size $trojan_csv_found] < 1024} {
    error "FATAL ERROR: power_trace_trojan.csv is missing or empty (< 1 KB) after xsim!"
}

puts "\[+\] Verified generated CSVs ([file size $golden_csv_found] B / [file size $trojan_csv_found] B)"
file copy -force $golden_csv_found "$REPO_ROOT/reports/power_trace_golden.csv"
file copy -force $trojan_csv_found "$REPO_ROOT/reports/power_trace_trojan.csv"
file copy -force $golden_csv_found "$BASE_REPS/power_trace_golden.csv"
file copy -force $trojan_csv_found "$BASE_REPS/power_trace_trojan.csv"
puts "\[+\] Synced CSVs to reports/ and references/implementation/reports/."

close_sim -quiet

# 3. RTL Elaboration Schematic Export (optional GUI artifact)
puts "\n\[*\] Elaborating RTL design for aes_128_trojan..."
set_property top aes_128_trojan [current_fileset]
update_compile_order -fileset sources_1
synth_design -rtl -top aes_128_trojan -part $PART_NAME
catch {
    write_schematic -format pdf -force "$REPO_ROOT/screenshots/vivado_schematic_rtl.pdf"
}
close_design -quiet

# 4. Out-of-Context Gate-Level Synthesis: Golden Core (aes_128)
puts "\n\[*\] Synthesizing Golden Core (aes_128) in Out-of-Context mode..."
set_property top aes_128 [current_fileset]
update_compile_order -fileset sources_1
synth_design -mode out_of_context -top aes_128 -part $PART_NAME
create_clock -period 100.000 -name clk [get_ports clk]
report_utilization    -file "$REPO_ROOT/reports/vivado_utilization_golden.txt"
report_power          -file "$REPO_ROOT/reports/vivado_power_golden.txt"
report_timing_summary -file "$REPO_ROOT/reports/vivado_timing_golden.txt"
close_design -quiet

file copy -force "$REPO_ROOT/reports/vivado_utilization_golden.txt" "$BASE_REPS/vivado_utilization_golden.txt"
file copy -force "$REPO_ROOT/reports/vivado_power_golden.txt"       "$BASE_REPS/vivado_power_golden.txt"
file copy -force "$REPO_ROOT/reports/vivado_timing_golden.txt"      "$BASE_REPS/vivado_timing_golden.txt"
puts "\[+\] Golden OOC synthesis reports saved & synced."

# 5. Out-of-Context Gate-Level Synthesis: Trojan Core (aes_128_trojan, DONT_TOUCH preserved)
puts "\n\[*\] Synthesizing Trojan Core (aes_128_trojan) in Out-of-Context mode..."
set_property top aes_128_trojan [current_fileset]
update_compile_order -fileset sources_1
synth_design -mode out_of_context -top aes_128_trojan -part $PART_NAME
create_clock -period 100.000 -name clk [get_ports clk]
report_utilization    -file "$REPO_ROOT/reports/vivado_utilization_trojan.txt"
report_power          -file "$REPO_ROOT/reports/vivado_power_trojan.txt"
report_timing_summary -file "$REPO_ROOT/reports/vivado_timing_trojan.txt"
close_design -quiet

file copy -force "$REPO_ROOT/reports/vivado_utilization_trojan.txt" "$BASE_REPS/vivado_utilization_trojan.txt"
file copy -force "$REPO_ROOT/reports/vivado_power_trojan.txt"       "$BASE_REPS/vivado_power_trojan.txt"
file copy -force "$REPO_ROOT/reports/vivado_timing_trojan.txt"      "$BASE_REPS/vivado_timing_trojan.txt"
puts "\[+\] Trojan OOC synthesis reports saved & synced."

puts "\n======================================================================"
puts "\[+\] VIVADO FULL FLOW EXECUTION FINISHED SUCCESSFULLY!"
puts "======================================================================"
exit
