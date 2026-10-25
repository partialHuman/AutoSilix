"""Logic synthesis adapter using Yosys."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from autosilix.adapters.base import ToolAdapter
from autosilix.runner import SubprocessRunner
from autosilix.stages import StageResult

if TYPE_CHECKING:
    from autosilix.artifacts import ArtifactManager
    from autosilix.config import AutoSilixConfig


class YosysAdapter(ToolAdapter):
    """Adapter for logic synthesis using Yosys."""

    def __init__(self) -> None:
        super().__init__(stage_name="synthesis", tool_name="yosys")

    def execute(
        self,
        config: AutoSilixConfig,
        artifacts: ArtifactManager,
        mock: bool = False,
    ) -> StageResult:
        log_path = artifacts.get_log_path(self.stage_name)
        result = self.create_pending_result(log_path)
        start_time = time.monotonic()

        out_netlist = artifacts.get_path("netlists/synthesized.v")
        out_report = artifacts.get_path("reports/synthesis.rpt")
        script_path = artifacts.get_path("config/synthesis.tcl")

        # Generate Yosys Tcl script
        tcl_content = self._generate_synthesis_script(config, out_netlist, out_report)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(tcl_content)

        if not self.is_available():
            if not mock:
                msg = "Yosys ('yosys') executable not found on system PATH"
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(f"[ERROR] {msg}\nInstall Yosys or execute with --mock for validation testing.\n")
                return self.mark_failed(result, time.monotonic() - start_time, msg, exit_code=127)

            # MOCK SYNTHESIS RUN
            return self._run_mock_synthesis(config, artifacts, result, start_time, out_netlist, out_report, log_path)

        # REAL YOSYS EXECUTION
        timeout = config.get_stage_timeout(self.stage_name)
        cmd = ["yosys", "-c", str(script_path)]

        sub_res = SubprocessRunner.run_command(cmd, log_file=log_path, cwd=artifacts.run_dir, timeout=timeout)
        duration = time.monotonic() - start_time

        if sub_res.returncode != 0 or sub_res.timed_out:
            err = "Yosys synthesis timed out" if sub_res.timed_out else f"Yosys failed with exit code {sub_res.returncode}"
            return self.mark_failed(result, duration, err, exit_code=sub_res.returncode)

        if not out_netlist.exists() or out_netlist.stat().st_size == 0:
            return self.mark_failed(result, duration, "Synthesized netlist was not generated or is empty", exit_code=1)

        return self.mark_passed(
            result,
            duration,
            ["netlists/synthesized.v", "reports/synthesis.rpt", "config/synthesis.tcl"],
            exit_code=0,
        )

    def _generate_synthesis_script(
        self,
        config: AutoSilixConfig,
        out_netlist: Path,
        out_report: Path,
    ) -> str:
        rtl_cmds = "\n".join([f"read_verilog -sv {p}" for p in config.design.rtl_files])
        flatten_flag = "-flatten" if config.synthesis.flatten else ""

        return f"""# AutoSilix Yosys Synthesis Script
# Design: {config.design.name}
# PDK: {config.pdk.name} ({config.pdk.variant})

# 1. Read RTL sources
{rtl_cmds}

# 2. Elaborate hierarchy
hierarchy -check -top {config.design.top_module}

# 3. High-level synthesis
synth -top {config.design.top_module} {flatten_flag}

# 4. Clean logic
opt -purge

# 5. Technology mapping
dfflegalize -cell $_DFF_P_ 01
techmap
opt -purge
abc -fast

# 6. Print design statistics to report file
tee -o {out_report.as_posix()} stat

# 7. Write synthesized gate-level netlist
write_verilog -noattr {out_netlist.as_posix()}
"""

    def _run_mock_synthesis(
        self,
        config: AutoSilixConfig,
        artifacts: ArtifactManager,
        result: StageResult,
        start_time: float,
        out_netlist: Path,
        out_report: Path,
        log_path: Path,
    ) -> StageResult:
        """Generate mock netlist and realistic synthesis report for unit testing."""
        # Calculate plausible gate counts based on design and constraints
        clock_period = config.constraints.clock_period
        if config.design.name == "sequence_detector":
            num_wires = 12
            num_cells = 18
            num_dffs = 3
            cell_area = 124.50 if clock_period >= 10.0 else 148.20  # Delay optimization adds buffer/cells
        elif config.design.name == "alu_accumulator":
            num_wires = 64
            num_cells = 112
            num_dffs = 11
            cell_area = 680.40
        else:
            num_wires = 20
            num_cells = 30
            num_dffs = 4
            cell_area = 200.00

        mock_netlist = f"""/* AutoSilix Synthesized Netlist (Mock Mode) */
/* Design: {config.design.name} */
/* Top module: {config.design.top_module} */

module {config.design.top_module} (
    input clk,
    input rst_n,
    input data_in,
    output seq_detected
);
    wire _0_, _1_, _2_, _3_;
    // Standard cell instances
    sky130_fd_sc_hd__dfxtp_1 _DFF_0_ (.CLK(clk), .D(_0_), .Q(_1_));
    sky130_fd_sc_hd__nand2_1 _GATE_0_ (.A(_1_), .B(data_in), .Y(_2_));
    sky130_fd_sc_hd__inv_1   _GATE_1_ (.A(_2_), .Y(seq_detected));
endmodule
"""
        out_netlist.write_text(mock_netlist, encoding="utf-8")

        mock_report = f"""=== {config.design.top_module} ===

   Number of wires:                 {num_wires}
   Number of wire bits:             {num_wires}
   Number of public wires:          {num_wires // 2}
   Number of public wire bits:      {num_wires // 2}
   Number of memories:               0
   Number of memory bits:            0
   Number of processes:              0
   Number of cells:                 {num_cells}
     $_DFF_P_                       {num_dffs}
     $_AND_                         {num_cells // 3}
     $_OR_                          {num_cells // 4}
     $_NOT_                         {num_cells - num_dffs - (num_cells // 3) - (num_cells // 4)}

   Chip area for module '{config.design.top_module}': {cell_area:.2f} um^2
"""
        out_report.write_text(mock_report, encoding="utf-8")

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("[AUTOSILIX] Running Yosys synthesis (Mock Engine)\n")
            f.write(f"[AUTOSILIX] Read {len(config.design.rtl_files)} RTL file(s)\n")
            f.write(f"[AUTOSILIX] Synthesized module: {config.design.top_module}\n")
            f.write(mock_report)

        duration = time.monotonic() - start_time
        return self.mark_passed(
            result,
            duration,
            ["netlists/synthesized.v", "reports/synthesis.rpt", "config/synthesis.tcl"],
            exit_code=0,
        )
