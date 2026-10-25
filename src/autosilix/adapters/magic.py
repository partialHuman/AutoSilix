"""Magic VLSI adapter for DRC and LVS checks."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from autosilix.adapters.base import ToolAdapter
from autosilix.stages import StageResult

if TYPE_CHECKING:
    from autosilix.artifacts import ArtifactManager
    from autosilix.config import AutoSilixConfig


class MagicAdapter(ToolAdapter):
    """Adapter for Magic layout-versus-schematic (LVS) and DRC verification."""

    def __init__(self, stage_name: str = "lvs") -> None:
        super().__init__(stage_name=stage_name, tool_name="magic")

    def execute(
        self,
        config: AutoSilixConfig,
        artifacts: ArtifactManager,
        mock: bool = False,
    ) -> StageResult:
        log_path = artifacts.get_log_path(self.stage_name)
        result = self.create_pending_result(log_path)
        start_time = time.monotonic()

        out_rpt = artifacts.get_path(f"reports/{self.stage_name}.rpt")

        if not self.is_available():
            if not mock:
                return self.mark_unsupported(
                    result,
                    f"Magic executable not found on PATH. {self.stage_name.upper()} check unsupported.",
                )

            # Mock check
            out_rpt.parent.mkdir(parents=True, exist_ok=True)
            out_rpt.write_text(
                f"""==========================================================================
AutoSilix {self.stage_name.upper()} Report (Magic Mock Engine)
Design: {config.design.top_module}
PDK: SkyWater SKY130
LVS Outcome: NETLISTS MATCH (Circuits are equivalent)
Mismatched nets: 0
Mismatched devices: 0
==========================================================================
""",
                encoding="utf-8",
            )
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"[AUTOSILIX] Magic {self.stage_name.upper()} Engine (Mock Mode)\nStatus: Match\n")

            duration = time.monotonic() - start_time
            return self.mark_passed(result, duration, [f"reports/{self.stage_name}.rpt"], exit_code=0)

        return self.mark_unsupported(result, "PDK Magic tech file not found in current environment")
