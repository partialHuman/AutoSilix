# AutoSilix Constraints & Timing Methodology

## 1. Synopsys Design Constraints (SDC)

Timing constraints are specified using standard SDC syntax.

### Clock Definition
Clocks are defined with `create_clock` specifying period and 50% duty cycle:

```tcl
create_clock -name clk -period 10.000 -waveform {0.000 5.000} [get_ports clk]
```

### Clock Margins
Clock uncertainty accounts for clock tree jitter and on-chip variation (OCV):

```tcl
set_clock_uncertainty 0.250 [get_clocks clk]
set_clock_transition 0.150 [get_clocks clk]
```

### I/O Boundary Timing
Input and output delays specify the external environment:

```tcl
set_input_delay -clock clk -max 2.000 [get_ports data_in]
set_input_delay -clock clk -min 0.500 [get_ports data_in]
set_output_delay -clock clk -max 2.000 [get_ports seq_detected]
set_output_delay -clock clk -min 0.500 [get_ports seq_detected]
set_load -pin_load 0.035 [get_ports seq_detected]
```

## 2. Corner Selection
The default OpenROAD reference script sets analysis at the nominal corner (`nom_tt_025C_1v80`). Multi-corner STA (including slow-slow `ss` and fast-fast `ff`) is documented as a roadmap enhancement.
