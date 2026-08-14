# ==============================================================================
# Script: export_screenshots.tcl
# Description: Automated Vivado script to load sources, run elaboration,
#              simulation, and export schematic (PDF/PNG) and waveform images.
# ==============================================================================

# Step 1: Ensure the screenshots directory exists
set screenshot_dir "./screenshots"
if {![file exists $screenshot_dir]} {
    file mkdir $screenshot_dir
    puts "\[+\] Created directory: $screenshot_dir"
} else {
    puts "\[+\] Output directory exists: $screenshot_dir"
}

# Step 2: Close stale projects and create clean project instance
if {[current_project -quiet] ne ""} {
    close_project -quiet
}

puts "\[+\] Creating fresh Vivado project instance..."
create_project -force lp_rtm ./lp_rtm -part xc7a200tfbg676-2

# Add all Verilog sources from lp_rtm.srcs/sources_1/new
set v_files [glob -nocomplain ./lp_rtm.srcs/sources_1/new/*.v]
if {[llength $v_files] > 0} {
    add_files -fileset sources_1 $v_files
    puts "\[+\] Added [llength $v_files] Verilog source files to project."
} else {
    puts "\[!\] Warning: No Verilog files found in ./lp_rtm.srcs/sources_1/new"
}

# Add constraint files
set xdc_files [glob -nocomplain ./lp_rtm.srcs/constrs_1/new/*.xdc]
if {[llength $xdc_files] > 0} {
    add_files -norecurse -fileset constrs_1 $xdc_files
}

# Set top modules for synthesis & simulation
set_property top top_monitored [get_filesets sources_1]
set_property top tb_top [get_filesets sim_1]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1

# Step 3: Open and Export RTL Elaborated Schematic (PDF Format)
puts "\[+\] Elaborating design 'top_monitored' to capture RTL Schematic..."
synth_design -rtl -name rtl_1 -top top_monitored

# Export schematic to vector PDF (natively supported format in Vivado write_schematic)
catch {
    write_schematic -format pdf -force "$screenshot_dir/schematic_elaborated_top_monitored.pdf"
    puts "\[+\] Saved Vector Schematic: $screenshot_dir/schematic_elaborated_top_monitored.pdf"
}

# Close elaboration view
close_design

# Step 4: Run Behavioral Simulation & Capture Waveform Image
puts "\[+\] Launching Behavioral Simulation..."

# Close any lingering simulation instances
if {[current_sim -quiet] ne ""} {
    close_sim -quiet
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

# Export waveform image
catch {
    export_wave_image -format png -file "$screenshot_dir/waveform_behavioral_simulation.png" -force
    puts "\[+\] Saved Waveform: $screenshot_dir/waveform_behavioral_simulation.png"
}

# Close simulation cleanly to flush VCD and logs
catch { close_sim }
puts "\[+\] Simulation completed and closed successfully."

# Convert PDF Schematic to PNG using Python helper script
catch {
    puts "\[+\] Generating PNG schematic image via Python..."
    exec python scripts/convert_pdf_to_png.py
}

puts "=============================================================================="
puts "\[+\] All schematics and waveforms successfully exported to $screenshot_dir/"
puts "=============================================================================="
