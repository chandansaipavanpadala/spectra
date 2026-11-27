set REPO_ROOT "D:/OneDrive - Amrita vishwa vidyapeetham/Amrita_college/4th_year/sem-7/Hardw/project/spectra"
set PROJ_DIR  [get_property DIRECTORY [current_project]]

# 1. Run 1000-cycle Behavioral Simulation & copy CSVs
set_property top tb_sidechannel [get_filesets sim_1]
set_property -name {xsim.simulate.runtime} -value {all} -objects [get_filesets sim_1]
launch_simulation
run all
set xsim_dir "$PROJ_DIR/spectra_vivado.sim/sim_1/behav/xsim"
file copy -force "$xsim_dir/power_trace_golden.csv" "$REPO_ROOT/reports/power_trace_golden.csv"
file copy -force "$xsim_dir/power_trace_trojan.csv" "$REPO_ROOT/reports/power_trace_trojan.csv"
close_sim -quiet

# 2. Golden Core OOC Synthesis & Reports
set_property top aes_128 [current_fileset]
synth_design -mode out_of_context -top aes_128 -part xc7a35tcsg324-1
create_clock -period 100.000 -name clk [get_ports clk]
report_utilization    -file "$REPO_ROOT/reports/vivado_utilization_golden.txt"
report_power          -file "$REPO_ROOT/reports/vivado_power_golden.txt"
report_timing_summary -file "$REPO_ROOT/reports/vivado_timing_golden.txt"
close_design -quiet

# 3. Trojan Core OOC Synthesis, Reports & Keep Schematic Open
set_property top aes_128_trojan [current_fileset]
synth_design -mode out_of_context -top aes_128_trojan -part xc7a35tcsg324-1
create_clock -period 100.000 -name clk [get_ports clk]
report_utilization    -file "$REPO_ROOT/reports/vivado_utilization_trojan.txt"
report_power          -file "$REPO_ROOT/reports/vivado_power_trojan.txt"
report_timing_summary -file "$REPO_ROOT/reports/vivado_timing_trojan.txt"
puts "=== SPECTRA NOVELTY FLOW COMPLETE (SCHEMATIC READY) ==="