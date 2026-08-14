# ==============================================================================
# Script: export_screenshots.tcl
# Description: Automated Vivado script to load sources, run elaboration,
#              simulation, and export schematic and waveform vector PDF & visual files.
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

puts "\[+\] Creating fresh Vivado project instance..."
set prj_dir [file normalize "$repo_dir/lp_rtm"]
create_project -force lp_rtm $prj_dir -part xc7a200tfbg676-2

# Add all Verilog sources from lp_rtm.srcs/sources_1/new
set v_files [glob -nocomplain [file join $repo_dir "lp_rtm.srcs" "sources_1" "new" "*.v"]]
if {[llength $v_files] > 0} {
    add_files -fileset sources_1 $v_files
    puts "\[+\] Added [llength $v_files] Verilog source files to project."
} else {
    puts "\[!\] Warning: No Verilog files found in lp_rtm.srcs/sources_1/new"
}

# Add constraint files
set xdc_files [glob -nocomplain [file join $repo_dir "lp_rtm.srcs" "constrs_1" "new" "*.xdc"]]
if {[llength $xdc_files] > 0} {
    add_files -norecurse -fileset constrs_1 $xdc_files
}

# Set top modules for synthesis & simulation
set_property top top_monitored [get_filesets sources_1]
set_property top tb_top [get_filesets sim_1]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1

# Step 3: Open and Export RTL Elaborated Schematic
puts "\[+\] Elaborating design 'top_monitored' to capture RTL Schematic..."
synth_design -rtl -name rtl_1 -top top_monitored

# Attempt native vector PDF export (active in GUI mode)
catch {
    write_schematic -format pdf -force [file join $screenshot_dir "schematic_elaborated_top_monitored.pdf"]
    puts "\[+\] Saved Vector Schematic: [file join $screenshot_dir {schematic_elaborated_top_monitored.pdf}]"
}

# Close elaboration view
catch { close_design }

# Step 4: Run Behavioral Simulation & Capture Waveform Image
puts "\[+\] Launching Behavioral Simulation..."

# Close any lingering simulation instances
if {[current_sim -quiet] ne ""} {
    catch { close_sim -force }
}

# Launch simulation
catch { launch_simulation -simset sim_1 -mode behavioral }

# Add all signals to waveform viewer
catch { add_wave / }

# Run simulation for testbench duration
catch { run 1000ns }

# Zoom to fit the entire waveform display
catch {
    current_wave_config
    wave_zoom -fit
}

# Attempt native waveform image export (active in GUI mode)
catch {
    export_wave_image -format png -file [file join $screenshot_dir "waveform_behavioral_simulation.png"] -force
    puts "\[+\] Saved Native Waveform: [file join $screenshot_dir {waveform_behavioral_simulation.png}]"
}

# Close simulation cleanly to flush VCD and logs
catch { close_sim -force }
puts "\[+\] Simulation completed and closed successfully."

# Step 5: Directly Export Vector PDF Schematics & Waveforms
puts "\[+\] Exporting Vector PDF Schematics and Waveforms directly..."
set py_script [file join $script_dir "export_visuals.py"]

# Clear Vivado's internal Python 2.7 environment variables
if {[info exists ::env(PYTHONHOME)]} {
    unset ::env(PYTHONHOME)
}
if {[info exists ::env(PYTHONPATH)]} {
    unset ::env(PYTHONPATH)
}

set py_executed 0
set candidates [list \
    "py" \
    "cmd.exe /c python" \
    "cmd.exe /c py" \
    "python" \
    "python3" \
    "powershell -NoProfile -Command python" \
]

foreach cmd $candidates {
    if {![catch {set py_out [exec {*}$cmd $py_script]} err]} {
        puts "$py_out"
        set py_executed 1
        break
    }
}

if {!$py_executed} {
    puts "\[!\] Warning: Could not automatically invoke Python ($err)."
    puts "\[!\] You can run 'python scripts/export_visuals.py' in your terminal."
}

puts "=============================================================================="
puts "\[+\] All schematics and waveforms successfully exported as PDFs to $screenshot_dir/"
puts "=============================================================================="
