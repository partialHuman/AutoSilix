# AutoSilix Development Roadmap

## Phase Progress Summary

- [x] **Phase 0 — Workspace & Environment Audit**: Baseline tooling audit, Git repository initialization, packaging structure (`pyproject.toml`, `Makefile`, `.gitignore`).
- [x] **Phase 1 — Working RTL Baseline**: Synthesizable Verilog sequence detector (`1011` overlapping detector with active-low reset), self-checking testbench, SDC timing constraints.
- [x] **Phase 2 — Python Framework Foundation**: Strict JSON schemas (`schemas/config.schema.json`, `schemas/manifest.schema.json`), configuration manager with path resolution, stage state machine, subprocess runner with timeouts, isolated run directories, and CLI core.
- [x] **Phase 3 — Real Synthesis Integration**: Yosys adapter with Tcl script generation, gate-level netlist output, cell area extraction, and mock test engine.
- [x] **Phase 4 — Physical-Design Reference Flow**: OpenROAD flow adapter supporting floorplanning, power distribution networks, placement, clock-tree synthesis, routing, and GDSII stream-out.
- [x] **Phase 5 — Metrics Extraction & Reporting**: Extraction of cell area, utilization, wire length, slack, and timing; Markdown, JSON, and CSV report export; PPA comparison engine with compatibility checks.
- [x] **Phase 6 — Robustness & CI**: Comprehensive pytest suite (50 passing unit and integration tests), failure-injection tests, and GitHub Actions CI pipelines (`tests.yml`, `rtl-checks.yml`).
- [x] **Phase 7 — Multi-Design Support & Experiments**: Second synthesizable design (`alu_accumulator`), clock period sweep experiment configurations, and cross-run trade-off comparison.
- [x] **Phase 8 — Release Preparation**: Clean documentation deliverables, architecture guides, and user manuals.

## Future Milestones
- [ ] Support for GlobalFoundries GF180MCU PDK.
- [ ] Integration with FlexRISC16 microprocessor core design.
- [ ] Multi-corner / multi-mode (MCMM) timing analysis.
- [ ] Automated hyperparameter sweeps with Pareto frontier extraction.
- [ ] Interactive layout viewing integration via KLayout Python API.
