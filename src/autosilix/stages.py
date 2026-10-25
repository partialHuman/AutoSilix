"""Stage definitions, state machine, and dependency enforcement."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class StageState(str, Enum):
    """Execution state of a workflow stage."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    NOT_RUN = "NOT_RUN"
    UNSUPPORTED = "UNSUPPORTED"


STAGE_ORDER: list[str] = [
    "rtl_simulation",
    "synthesis",
    "floorplan",
    "power_planning",
    "placement",
    "cts",
    "routing",
    "sta",
    "drc",
    "lvs",
    "gds_export",
]

# Standard direct prerequisites for each stage
STAGE_DEPENDENCIES: dict[str, list[str]] = {
    "rtl_simulation": [],
    "synthesis": ["rtl_simulation"],
    "floorplan": ["synthesis"],
    "power_planning": ["floorplan"],
    "placement": ["power_planning"],
    "cts": ["placement"],
    "routing": ["cts"],
    "sta": ["routing"],
    "drc": ["routing"],
    "lvs": ["routing"],
    "gds_export": ["routing"],
}


@dataclass
class StageResult:
    """Outcome and execution metadata for a single stage."""

    name: str
    state: StageState = StageState.PENDING
    start_time: str | None = None
    end_time: str | None = None
    duration_seconds: float = 0.0
    exit_code: int | None = None
    log_file: str | None = None
    error_summary: str | None = None
    artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": round(self.duration_seconds, 3),
            "exit_code": self.exit_code,
            "log_file": self.log_file,
            "error_summary": self.error_summary,
            "artifacts": self.artifacts,
        }


@dataclass
class StageContract:
    """Defines inputs, expected outputs, and requirements for a stage."""

    name: str
    description: str
    prerequisites: list[str]
    required_inputs: list[str]
    expected_outputs: list[str]
    default_timeout: int = 300


STAGE_CONTRACTS: dict[str, StageContract] = {
    "rtl_simulation": StageContract(
        name="rtl_simulation",
        description="Functional verification and testbench simulation of RTL sources",
        prerequisites=[],
        required_inputs=["rtl_files", "tb_files"],
        expected_outputs=["simulation.log"],
        default_timeout=120,
    ),
    "synthesis": StageContract(
        name="synthesis",
        description="Logic synthesis and technology mapping to target standard cells",
        prerequisites=["rtl_simulation"],
        required_inputs=["rtl_files"],
        expected_outputs=["netlists/synthesized.v", "reports/synthesis.rpt"],
        default_timeout=300,
    ),
    "floorplan": StageContract(
        name="floorplan",
        description="Die and core dimension initialization, pin placement, and boundary definition",
        prerequisites=["synthesis"],
        required_inputs=["netlists/synthesized.v"],
        expected_outputs=["databases/floorplan.def"],
        default_timeout=180,
    ),
    "power_planning": StageContract(
        name="power_planning",
        description="Power Distribution Network (PDN) synthesis and ring/stripe generation",
        prerequisites=["floorplan"],
        required_inputs=["databases/floorplan.def"],
        expected_outputs=["databases/pdn.def"],
        default_timeout=180,
    ),
    "placement": StageContract(
        name="placement",
        description="Global and detailed standard-cell placement and cell legalization",
        prerequisites=["power_planning"],
        required_inputs=["databases/pdn.def"],
        expected_outputs=["databases/placed.def"],
        default_timeout=300,
    ),
    "cts": StageContract(
        name="cts",
        description="Clock Tree Synthesis and clock distribution buffer insertion",
        prerequisites=["placement"],
        required_inputs=["databases/placed.def"],
        expected_outputs=["databases/cts.def"],
        default_timeout=300,
    ),
    "routing": StageContract(
        name="routing",
        description="Global and detailed wire routing and DRC violation cleanup",
        prerequisites=["cts"],
        required_inputs=["databases/cts.def"],
        expected_outputs=["databases/routed.def"],
        default_timeout=600,
    ),
    "sta": StageContract(
        name="sta",
        description="Post-route Static Timing Analysis (slack, critical paths, transition checks)",
        prerequisites=["routing"],
        required_inputs=["databases/routed.def"],
        expected_outputs=["reports/sta.rpt"],
        default_timeout=180,
    ),
    "drc": StageContract(
        name="drc",
        description="Design Rule Checking against PDK physical manufacturing decks",
        prerequisites=["routing"],
        required_inputs=["databases/routed.def"],
        expected_outputs=["reports/drc.rpt"],
        default_timeout=300,
    ),
    "lvs": StageContract(
        name="lvs",
        description="Layout Versus Schematic netlist and device geometry equivalence check",
        prerequisites=["routing"],
        required_inputs=["databases/routed.def", "netlists/synthesized.v"],
        expected_outputs=["reports/lvs.rpt"],
        default_timeout=300,
    ),
    "gds_export": StageContract(
        name="gds_export",
        description="Stream-out of finalized physical layout into standard GDSII stream format",
        prerequisites=["routing"],
        required_inputs=["databases/routed.def"],
        expected_outputs=["layout/final.gds"],
        default_timeout=180,
    ),
}
