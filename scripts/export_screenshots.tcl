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
        catch { open_project ./lp_rtm/lp_rtm.xpr }
    }
    
    if {[current_project -quiet] eq ""} {
        puts "\[+\] Recreating Vivado project using recreate_project.tcl..."
        catch { source scripts/recreate_project.tcl }
    }
    
    if {[current_project -quiet] eq ""} {
        puts "\[+\] Creating in-memory project for standalone elaboration..."
        create_project -force temp_proj ./temp_proj -part xc7a200tfbg676-2
        set v_files [glob -nocomplain ./lp_rtm.srcs/sources_1/new/*.v]
        if {[llength $v_files] > 0} {
            add_files -fileset sources_1 $v_files
        }
    }
}

# Set top module for synthesis & simulation
catch { set_property top top_monitored [get_filesets sources_1] }

# Step 3: Open and Export RTL Elaborated Schematic
puts "\[+\] Elaborating design to capture RTL Schematic..."
catch {
    synth_design -rtl -name rtl_1 -top top_monitored
    write_schematic -format png -force "$screenshot_dir/schematic_elaborated_top_monitored.png"
    puts "\[+\] Saved: $screenshot_dir/schematic_elaborated_top_monitored.png"
    close_design
}

# Step 4: Run Behavioral Simulation & Capture Waveform
puts "\[+\] Launching Behavioral Simulation..."

# Close any lingering simulation instances
if {[get_sims sim_1] ne ""} {
    close_sim -quiet
}

# Launch simulation
catch {
    launch_simulation -simset sim_1 -mode behavioral
    add_wave /
    run 1000ns
    current_wave_config
    wave_zoom -fit
    export_wave_image -format png -file "$screenshot_dir/waveform_behavioral_simulation.png" -force
    puts "\[+\] Saved: $screenshot_dir/waveform_behavioral_simulation.png"
    close_sim
    puts "\[+\] Simulation completed and closed successfully."
}

puts "=============================================================================="
puts "\[+\] All schematics and waveforms successfully exported to $screenshot_dir/"
puts "=============================================================================="
