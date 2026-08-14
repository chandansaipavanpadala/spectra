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

# Step 2: Ensure Vivado Project is Open or Recreated
if {[current_project -quiet] eq ""} {
    if {[file exists "./lp_rtm/lp_rtm.xpr"]} {
        puts "\[+\] Opening existing Vivado project: ./lp_rtm/lp_rtm.xpr"
        open_project ./lp_rtm/lp_rtm.xpr
    } elseif {[file exists "./scripts/recreate_project.tcl"]} {
        puts "\[+\] Recreating Vivado project using recreate_project.tcl..."
        source scripts/recreate_project.tcl
    } else {
        puts "\[+\] Reading Verilog source files..."
        read_verilog [glob ./lp_rtm.srcs/sources_1/new/*.v]
    }
}

# Step 3: Open and Export RTL Elaborated Schematic
puts "\[+\] Elaborating design to capture RTL Schematic..."
synth_design -rtl -name rtl_1

# Export full elaborated schematic image
write_schematic -format png -force "$screenshot_dir/schematic_elaborated_top_monitored.png"
puts "\[+\] Saved: $screenshot_dir/schematic_elaborated_top_monitored.png"

# Close elaboration view
close_design

# Step 4: Run Behavioral Simulation & Capture Waveform
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
catch {
    current_wave_config
    wave_zoom -fit
}

# Export the waveform viewer window to PNG image
catch {
    export_wave_image -format png -file "$screenshot_dir/waveform_behavioral_simulation.png" -force
    puts "\[+\] Saved: $screenshot_dir/waveform_behavioral_simulation.png"
}

# Close simulation cleanly to flush VCD and logs
close_sim
puts "\[+\] Simulation completed and closed successfully."

puts "=============================================================================="
puts "\[+\] All schematics and waveforms successfully exported to $screenshot_dir/"
puts "=============================================================================="
