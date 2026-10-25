# ==============================================================================
# SDC Constraints for Sequence Detector (SkyWater SKY130 Target)
# Clock: 100 MHz (10.0 ns period)
# ==============================================================================

# Current design
current_design sequence_detector

# Clock definition: 10.0 ns (100 MHz) with 50% duty cycle on port 'clk'
create_clock -name clk -period 10.000 -waveform {0.000 5.000} [get_ports clk]

# Clock uncertainty (jitter + margin)
set_clock_uncertainty 0.250 [get_clocks clk]

# Clock transition
set_clock_transition 0.150 [get_clocks clk]

# Input delays relative to clk
set_input_delay -clock clk -max 2.000 [get_ports data_in]
set_input_delay -clock clk -min 0.500 [get_ports data_in]
set_input_delay -clock clk -max 2.000 [get_ports rst_n]
set_input_delay -clock clk -min 0.500 [get_ports rst_n]

# Output delays relative to clk
set_output_delay -clock clk -max 2.000 [get_ports seq_detected]
set_output_delay -clock clk -min 0.500 [get_ports seq_detected]

# Output load (capacitance in pF)
set_load -pin_load 0.035 [get_ports seq_detected]

# Input drive / transition
set_input_transition 0.100 [get_ports data_in]
set_input_transition 0.100 [get_ports rst_n]
