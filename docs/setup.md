# AutoSilix Setup & Environment Guide

## 1. Prerequisites

AutoSilix is designed to run natively on Linux, macOS, and Windows (via Python or WSL2).

### Required Base Dependencies
- **Python**: `>=3.10` (tested on 3.10, 3.11, 3.12, 3.13, 3.14)
- **Git**: `>=2.20`

### Optional EDA Toolchain
To run real synthesis and physical design flows:
- **RTL Simulator**: [Icarus Verilog](http://iverilog.icarus.com/) (`iverilog`, `vvp`) or [Verilator](https://www.veripool.org/verilator/)
- **Logic Synthesis**: [Yosys](https://yosyshq.net/yosys/)
- **Physical Design**: [OpenROAD](https://theopenroadproject.org/)
- **Layout Inspection & DRC**: [KLayout](https://www.klayout.de/)
- **Physical Verification (DRC/LVS)**: [Magic VLSI](http://opencircuitdesign.com/magic/)
- **Target PDK**: [SkyWater SKY130](https://github.com/google/skywater-pdk)

> [!NOTE]
> AutoSilix includes a self-contained Mock Engine (`--mock`). You can develop, test, and validate the complete orchestration, configuration schemas, reports, and comparisons without having external EDA tools installed.

## 2. Installation

Clone the repository and install in editable development mode:

```bash
git clone https://github.com/your-org/autosilix.git
cd autosilix

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install AutoSilix with dev dependencies
pip install -e ".[dev]"
```

## 3. Verifying Installation

Check toolchain discovery:

```bash
autosilix tools
```

Validate a sample design configuration:

```bash
autosilix validate --config configs/designs/sequence_detector.yaml
```

Run a test implementation in mock mode:

```bash
autosilix run --config configs/designs/sequence_detector.yaml --mock
```
