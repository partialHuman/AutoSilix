# AutoSilix Configuration Specification

All AutoSilix design workflows are configured via declarative YAML files validated against `schemas/config.schema.json`.

## Schema Structure

```yaml
schema_version: "1.0.0"

design:
  name: "sequence_detector"               # Identifier for runs and directory naming
  top_module: "sequence_detector"         # Top-level Verilog module name
  rtl_files:                              # List of synthesizable RTL sources
    - "designs/sequence_detector/rtl/sequence_detector.v"
  tb_files:                               # List of testbench sources for simulation
    - "designs/sequence_detector/tb/tb_sequence_detector.v"
  constraints_file: "designs/sequence_detector/constraints/sky130_constraints.sdc"

pdk:
  name: "sky130"                          # Target Process Design Kit
  variant: "sky130_fd_sc_hd"              # High-density standard cell variant
  std_cell_library: "sky130_fd_sc_hd"
  pdk_root: "/usr/local/share/pdk"

constraints:
  clock_period: 10.0                      # Target clock period in nanoseconds
  clock_port: "clk"                       # Clock net/port name
  clock_uncertainty: 0.25                 # Clock jitter margin
  input_delay: 2.0                        # Max input arrival delay
  output_delay: 2.0                       # Max output required delay
  time_unit: "ns"
  cap_unit: "pF"

physical:
  core_utilization: 0.35                  # Standard cell target utilization (0.01 - 0.99)
  core_aspect_ratio: 1.0                  # Height-to-width ratio
  core_margin: 10.0                       # Core boundary spacing (um)

synthesis:
  strategy: "AREA"                        # AREA, DELAY, or BALANCED
  flatten: true                           # Flatten hierarchy during logic optimization
  abc_clock_period: 10000.0               # ABC clock constraint in picoseconds

flow:
  stages:                                 # Selected implementation stages
    - rtl_simulation
    - synthesis
    - floorplan
    - power_planning
    - placement
    - cts
    - routing
    - sta
    - gds_export
  timeouts:                               # Per-stage timeout limits (seconds)
    rtl_simulation: 60
    synthesis: 180
    routing: 300
  fail_fast: true                         # Stop immediately on stage failure
```
