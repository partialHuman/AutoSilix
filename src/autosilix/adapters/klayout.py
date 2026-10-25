"""KLayout adapter for layout inspection and DRC verification."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from autosilix.adapters.base import ToolAdapter
from autosilix.stages import StageResult

if TYPE_CHECKING:
    from autosilix.artifacts import ArtifactManager
    from autosilix.config import AutoSilixConfig


class KLayoutAdapter(ToolAdapter):
    """Adapter for KLayout DRC and geometry inspection."""

    def __init__(self) -> None:
        super().__init__(stage_name="drc", tool_name="klayout")

    def execute(
        self,
        config: AutoSilixConfig,
        artifacts: ArtifactManager,
        mock: bool = False,
    ) -> StageResult:
        log_path = artifacts.get_log_path(self.stage_name)
        result = self.create_pending_result(log_path)
        start_time = time.monotonic()

        out_rpt = artifacts.get_path("reports/drc.rpt")

        if not self.is_available():
            if not mock:
                return self.mark_unsupported(
                    result,
                    "KLayout executable not found on PATH. Physical DRC check skipped.",
                )

            # Mock DRC check
            out_rpt.parent.mkdir(parents=True, exist_ok=True)
            out_rpt.write_text(
                f"""==========================================================================
AutoSilix DRC Report (KLayout Mock Engine)
Design: {config.design.top_module}
PDK Deck: SkyWater SKY130 HD DRC (Rev A)
DRC Clean: YES
Violations found: 0
==========================================================================
""",
                encoding="utf-8",
            )
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("[AUTOSILIX] KLayout DRC Engine (Mock Mode)\nDRC Violations: 0\n")

            duration = time.monotonic() - start_time
            return self.mark_passed(result, duration, ["reports/drc.rpt"], exit_code=0)

        # Real execution if available
        # klayout -b -r drc_deck.lydrc -rd input_gds=...
        return self.mark_unsupported(result, "PDK DRC deck not configured in current environment")
