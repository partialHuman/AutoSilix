# AutoSilix Metrics & Provenance Engine

AutoSilix decouples metrics extraction from tool execution. Every metric is associated with provenance metadata:

```json
{
  "cell_area": {
    "name": "cell_area",
    "value": 124.5,
    "unit": "um^2",
    "stage": "synthesis",
    "source_file": "reports/synthesis.rpt",
    "parser_version": "1.0.0"
  }
}
```

## Tracked Implementation Metrics

### Area Metrics
- `cell_area`: Total synthesized cell area in $\mu\text{m}^2$.
- `cell_count`: Total cell instance count mapped to target gates.
- `sequential_cell_count`: Number of flip-flops / latches.
- `die_area`: Outer boundary dimensions of the chip die ($\mu\text{m}^2$).
- `core_area`: Internal standard-cell placement region ($\mu\text{m}^2$).
- `core_utilization`: Core area utilization percentage ($0.0 - 100\%$).

### Timing & Performance Metrics
- `clock_target`: Constrained clock period target ($\text{ns}$).
- `setup_slack`: Setup timing margin on the worst path ($\text{ns}$).
- `worst_negative_slack` (WNS): Maximum timing violation magnitude ($\text{ns}$).
- `total_negative_slack` (TNS): Sum of negative slack over all failing endpoints ($\text{ns}$).
- `critical_path_delay`: Total data arrival delay from launch clock to capture latch ($\text{ns}$).
- `clock_skew`: Clock arrival time variation across registers ($\text{ns}$).

### Routing & Physical Quality
- `wire_length`: Total routed interconnect length ($\mu\text{m}$).
- `unrouted_nets`: Count of signal nets that failed detailed routing.
- `route_drc_violations`: Routing geometry violations reported by the router.
- `clock_buffer_count`: Buffer/inverter instances inserted during clock tree synthesis.
