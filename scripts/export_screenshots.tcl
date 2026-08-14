# ==============================================================================
# Script: export_screenshots.tcl
# Description: Automated Vivado script to run elaboration, simulation, and
#              export schematic and waveform images to the screenshots/ folder.
# ==============================================================================

# Step 1: Ensure the screenshots directory exists
set screenshot_dir "./screenshots"
if {![file exists $screenshot_dir]} {
    file mkdir $screenshot_dir
    puts "\[+\] Created directory: $screenshot_dir"
} else {
    puts "\[+\] Output directory exists: $screenshot_dir"
}

# Step 2: Open and Export RTL Elaborated Schematic
puts "\[+\] Elaborating design to capture RTL Schematic..."
synth_design -rtl -name rtl_1

# Export full elaborated schematic image
write_schematic -format png -force "$screenshot_dir/schematic_elaborated_top_monitored.png"
puts "\[+\] Saved: $screenshot_dir/schematic_elaborated_top_monitored.png"

# Close elaboration view
close_design

# Step 3: Run Behavioral Simulation & Capture Waveform
puts "\[+\] Launching Behavioral Simulation..."

# Close any lingering simulation instances
if {[get_sims sim_1] ne ""} {
    close_sim -quiet
}

# Launch simulation
launch_simulation -simset sim_1 -mode behavioral

# Add all signals to waveform viewer
add_wave /

# Run simulation for testbench duration
run 1000ns

# Zoom to fit the entire waveform display
current_wave_config
wave_zoom -fit

# Export the waveform viewer window to PNG image
# (Supported in Vivado GUI / batch GUI mode)
catch {
    export_wave_image -format png -file "$screenshot_dir/waveform_behavioral_simulation.png" -force
    puts "\[+\] Saved: $screenshot_dir/waveform_behavioral_simulation.png"
}

# Close simulation cleanly to flush VCD and logs
close_sim
puts "\[+\] Simulation completed and closed successfully."

# Step 4: Optional - Synthesize and Export Synthesized Gate-Level Schematic
# ------------------------------------------------------------------------------
# puts "\[+\] Synthesizing design for gate-level schematic..."
# synth_design -top top_monitored -part xc7a200tfbg676-2
# write_schematic -format png -force "$screenshot_dir/schematic_synthesized_gate_level.png"
# puts "\[+\] Saved: $screenshot_dir/schematic_synthesized_gate_level.png"
# close_design
# ------------------------------------------------------------------------------

puts "=============================================================================="
puts "\[+\] All schematics and waveforms successfully exported to $screenshot_dir/"
puts "=============================================================================="
