# ==============================================================================
# Base Paper Vivado Simulation TCL Script
# Target: tb_sidechannel_base (Section IV-A IEEE JIOT 2024)
# ==============================================================================

set SCRIPT_DIR [file normalize [file dirname [info script]]]
set BASE_DIR   [file normalize "$SCRIPT_DIR/.."]
set REPO_ROOT  [file normalize "$BASE_DIR/../.."]
set PROJ_DIR   [file normalize "D:/spectra_vivado/base_sim_project"]
set PROJ_NAME  "base_sim"
set PART_NAME  "xc7a35tcsg324-1"

puts "======================================================================"
puts "\[+\] BASE PAPER VIVADO SIMULATION FLOW (tb_sidechannel_base)"
puts "======================================================================"

file mkdir "$BASE_DIR/reports"
file mkdir "$BASE_DIR/screenshots"

# Create clean project in scratch directory
if {[file exists $PROJ_DIR]} {
    catch { file delete -force $PROJ_DIR }
}
create_project $PROJ_NAME $PROJ_DIR -part $PART_NAME -force

# Add Sources
add_files -fileset sources_1 [list \
    "$BASE_DIR/src/aes_128_base.v" \
    "$BASE_DIR/src/aes_128_trojan_base.v" \
]

add_files -fileset sim_1 [list \
    "$BASE_DIR/src/tb_sidechannel_base.v" \
]

set_property top aes_128_trojan_base [current_fileset]
set_property top tb_sidechannel_base [get_filesets sim_1]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1

puts "\n\[*\] Launching Behavioral Simulation (xsim)..."
set_property -name {xsim.simulate.runtime} -value {all} -objects [get_filesets sim_1]
launch_simulation -simset [get_filesets sim_1] -mode behavioral

puts "\[*\] Running simulation to completion..."
run all

# Copy generated CSVs
set xsim_run_dir [file normalize "$PROJ_DIR/${PROJ_NAME}.sim/sim_1/behav/xsim"]
set csv_candidates [list $xsim_run_dir [pwd] "$BASE_DIR" "$PROJ_DIR"]

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

if {$golden_csv_found eq "" || $trojan_csv_found eq ""} {
    set found_golden [glob -nocomplain -directory $PROJ_DIR -types f "*power_trace_golden.csv*"]
    if {[llength $found_golden] > 0} { set golden_csv_found [lindex $found_golden 0] }
    set found_trojan [glob -nocomplain -directory $PROJ_DIR -types f "*power_trace_trojan.csv*"]
    if {[llength $found_trojan] > 0} { set trojan_csv_found [lindex $found_trojan 0] }
}

if {$golden_csv_found ne "" && $trojan_csv_found ne ""} {
    puts "\[+\] Found generated CSV traces at: $golden_csv_found"
    file copy -force $golden_csv_found "$BASE_DIR/reports/power_trace_golden.csv"
    file copy -force $trojan_csv_found "$BASE_DIR/reports/power_trace_trojan.csv"
    # Also sync top-level reports
    file copy -force $golden_csv_found "$REPO_ROOT/reports/power_trace_golden.csv"
    file copy -force $trojan_csv_found "$REPO_ROOT/reports/power_trace_trojan.csv"
    puts "\[+\] Successfully copied hardware traces to reports/."
} else {
    puts "\[!\] Error: CSV traces not found after simulation!"
}

close_sim -quiet
puts "\n\[+\] Base Vivado Simulation Finished Successfully."
exit

