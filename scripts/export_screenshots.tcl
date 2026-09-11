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
if {[current_project -quiet] ne ""} {
    close_project -quiet
}

puts "\[+\] Creating fresh SPECTRA Vivado project instance..."
set prj_dir [file normalize "$repo_dir/spectra_prj"]
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
write_schematic -format pdf -force $pdf_golden

# Step 4: Open and Export RTL Elaborated Schematic for Trojan AES-128
puts "\[+\] Elaborating Trojan-Infected Core 'aes_128_trojan' to capture RTL Schematic..."
synth_design -rtl -name rtl_trojan -top aes_128_trojan

set pdf_trojan "$screenshot_dir/schematic_elaborated_aes_128_trojan.pdf"
puts "\[+\] Exporting Trojan RTL Schematic vector PDF: $pdf_trojan"
write_schematic -format pdf -force $pdf_trojan

puts "\[+\] SPECTRA Vivado TCL export script executed successfully."
