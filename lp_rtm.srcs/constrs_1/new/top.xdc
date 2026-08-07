##################################################################################
# Timing Constraints
# 100 MHz Clock Constraint on port 'clk' (10.000 ns Period, 50% Duty Cycle)
##################################################################################
create_clock -period 10.000 -name clk -waveform {0.000 5.000} [get_ports clk]

##################################################################################
# IO Standard Constraints - LVCMOS33
##################################################################################
set_property IOSTANDARD LVCMOS33 [get_ports clk]
set_property IOSTANDARD LVCMOS33 [get_ports rst]
set_property IOSTANDARD LVCMOS33 [get_ports enable]
set_property IOSTANDARD LVCMOS33 [get_ports test_mode]
set_property IOSTANDARD LVCMOS33 [get_ports corner_case_flag]

# 32-bit Data Input Bus
set_property IOSTANDARD LVCMOS33 [get_ports {data_in[*]}]

# 32-bit Key Input Bus
set_property IOSTANDARD LVCMOS33 [get_ports {key_in[*]}]

# 32-bit Data Output Bus
set_property IOSTANDARD LVCMOS33 [get_ports {data_out[*]}]
