# AutoSilix Testing Strategy & Verification Guide

## 1. Automated Test Suite

AutoSilix employs a comprehensive test suite using `pytest` and `ruff`:

- **Unit Tests (`tests/unit/`)**:
  - `test_config.py`: Schema validation, YAML parsing, path resolution, missing file handling.
  - `test_toolchain.py`: Tool discovery, version parsing, git status.
  - `test_stages.py`: State transitions, dependencies, contracts.
  - `test_artifacts.py`: Directory creation, collision prevention, config snapshots, SHA256.
  - `test_manifest.py`: Atomic write, persistence, schema conformance.
  - `test_runner.py`: Process spawning, return codes, log capture, timeout enforcement.
  - `test_metrics.py`: Parsing synthesis, floorplan, CTS, routing, and STA reports.
  - `test_report.py`: Markdown, JSON, and CSV report formatting.
  - `test_compare.py`: Deltas, percentage changes, incompatible design rejection.
  - `test_adapters.py`: Adapter interfaces, Tcl script generation.
  - `test_cli.py`: All CLI entrypoints and exit codes.

- **Integration Tests (`tests/integration/`)**:
  - `test_failure_injection.py`: Simulates missing tools, missing files, collision runs, fail-fast behavior.
  - `test_e2e_mock_flow.py`: Full end-to-end runs of `sequence_detector` and `alu_accumulator`.
  - `test_rtl_simulation.py`: Verifies synthesizable Verilog code and testbench coverage.

## 2. Running Tests

```bash
# Run full pytest suite
python -m pytest tests/

# Run with verbose output and coverage
python -m pytest -v tests/

# Run linting checks
python -m ruff check src tests
```
