# ==============================================================================
# Script: export_screenshots.tcl
# Description: Automated Vivado script for SPECTRA platform to load sources,
#              run RTL elaboration for aes_128 & aes_128_trojan, and export schematics.
# ==============================================================================

# Determine absolute project directory paths
set script_path [file normalize [info script]]
set script_dir [file dirname $script_path]
set repo_dir [file dirname $script_dir]

# Step 1: Ensure output directories exist
set screenshot_dir [file normalize "$repo_dir/screenshots"]
set reports_dir [file normalize "$repo_dir/reports"]

if {![file exists $screenshot_dir]} {
    file mkdir $screenshot_dir
    puts "\[+\] Created directory: $screenshot_dir"
} else {
    puts "\[+\] Output directory exists: $screenshot_dir"
}

if {![file exists $reports_dir]} {
    file mkdir $reports_dir
}

# Step 2: Close stale projects and create clean project instance
catch {config_webtalk -user off}
catch {set_param project.enableCentralDir 0}

if {[current_project -quiet] ne ""} {
    close_project -quiet
}

puts "\[+\] Creating fresh SPECTRA Vivado project instance..."
set prj_dir [file normalize "$repo_dir/spectra_prj"]
catch {file delete -force $prj_dir}
create_project -force spectra_prj $prj_dir -part xc7a200tfbg676-2

# Add all Verilog sources from src/ or spectra.srcs/sources_1/new
set v_files [glob -nocomplain [file join $repo_dir "src" "*.v"]]
if {[llength $v_files] == 0} {
    set v_files [glob -nocomplain [file join $repo_dir "spectra.srcs" "sources_1" "new" "*.v"]]
}

if {[llength $v_files] > 0} {
    add_files -fileset sources_1 $v_files
    puts "\[+\] Added [llength $v_files] Verilog source files to SPECTRA project."
} else {
    puts "\[!\] Warning: No Verilog files found in src/ or spectra.srcs/sources_1/new"
}

# Set top modules for synthesis & simulation
set_property top aes_128 [get_filesets sources_1]
set_property top tb_sidechannel [get_filesets sim_1]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1

# Step 3: Open and Export RTL Elaborated Schematic for Golden AES-128
puts "\[+\] Elaborating Golden Core 'aes_128' to capture RTL Schematic..."
synth_design -rtl -name rtl_golden -top aes_128

set pdf_golden "$screenshot_dir/schematic_elaborated_aes_128.pdf"
puts "\[+\] Exporting Golden RTL Schematic vector PDF: $pdf_golden"
if {[catch {write_schematic -format pdf -force $pdf_golden} err_gold]} {
    puts "\[!\] Warning: write_schematic golden returned: $err_gold"
}
close_design

# Step 4: Open and Export RTL Elaborated Schematic for Trojan AES-128
puts "\[+\] Elaborating Trojan-Infected Core 'aes_128_trojan' to capture RTL Schematic..."
set_property top aes_128_trojan [get_filesets sources_1]
update_compile_order -fileset sources_1
synth_design -rtl -name rtl_trojan -top aes_128_trojan

set pdf_trojan "$screenshot_dir/schematic_elaborated_aes_128_trojan.pdf"
puts "\[+\] Exporting Trojan RTL Schematic vector PDF: $pdf_trojan"
if {[catch {write_schematic -format pdf -force $pdf_trojan} err_troj]} {
    puts "\[!\] Warning: write_schematic trojan returned: $err_troj"
}
close_design

# Reset top back to aes_128 for sources_1 and tb_sidechannel for sim_1
set_property top aes_128 [get_filesets sources_1]
set_property top tb_sidechannel [get_filesets sim_1]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1

# Step 5: Launch Behavioral Simulation to dump power-switching telemetry traces
puts "\[+\] Launching Behavioral Simulation (tb_sidechannel)..."
set sim_xsim_dir [file normalize "$prj_dir/spectra_prj.sim/sim_1/behav/xsim"]
file mkdir [file join $sim_xsim_dir "reports"]
file mkdir $reports_dir

if {[catch {
    launch_simulation
    run all
    close_sim
} sim_err]} {
    puts "\[!\] launch_simulation note: $sim_err"
}

# Copy traces to repo reports directory if generated in simulation directory
if {[file exists [file join $sim_xsim_dir "reports" "power_trace_golden.csv"]]} {
    file copy -force [file join $sim_xsim_dir "reports" "power_trace_golden.csv"] [file join $reports_dir "power_trace_golden.csv"]
    file copy -force [file join $sim_xsim_dir "reports" "power_trace_trojan.csv"] [file join $reports_dir "power_trace_trojan.csv"]
    puts "\[+\] Power traces successfully generated and copied to $reports_dir"
}

puts "\[+\] SPECTRA Vivado TCL export script executed successfully."
