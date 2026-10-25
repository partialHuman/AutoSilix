# AutoSilix Troubleshooting Guide

## 1. Common Issues and Resolutions

### `ToolNotFoundError: Executable not found: 'iverilog' / 'yosys' / 'openroad'`
- **Cause**: The external EDA tool is not present on your system's PATH.
- **Resolution**:
  - Install the tool via your system package manager (e.g. `apt-get install iverilog yosys` on Ubuntu) or build from source.
  - Or run AutoSilix with `--mock` to validate flow orchestration without external binaries:
    ```bash
    autosilix run --config configs/designs/sequence_detector.yaml --mock
    ```

### `ValidationError: Configuration validation failed`
- **Cause**: The YAML file violates `schemas/config.schema.json`.
- **Resolution**:
  - Run `autosilix validate --config <path>` to see the exact schema field and line that failed.

### `IncompatibleComparisonError: Incompatible run comparison`
- **Cause**: Attempted to compare two runs targeting different RTL designs (e.g. `sequence_detector` vs `alu_accumulator`).
- **Resolution**:
  - Compare runs that share the same design and PDK to ensure PPA metrics reflect valid engineering trade-offs.

### `ArtifactError: Run directory already exists and is not empty`
- **Cause**: An explicit `--run-id` was supplied that collides with a previous run.
- **Resolution**:
  - Provide a new run ID or omit `--run-id` to let AutoSilix generate a collision-free timestamped ID automatically.
