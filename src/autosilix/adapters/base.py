"""Base class and common contract for EDA tool adapters."""

from __future__ import annotations

import abc
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from autosilix.stages import StageResult, StageState
from autosilix.toolchain import ToolchainDetector

if TYPE_CHECKING:
    from autosilix.artifacts import ArtifactManager
    from autosilix.config import AutoSilixConfig


class ToolAdapter(abc.ABC):
    """Abstract interface for wrapping external EDA tools."""

    def __init__(self, stage_name: str, tool_name: str) -> None:
        self.stage_name = stage_name
        self.tool_name = tool_name

    def is_available(self) -> bool:
        """Check if the required tool executable exists on PATH."""
        info = ToolchainDetector.inspect_tool(self.tool_name)
        return info.available

    def get_version(self) -> str | None:
        info = ToolchainDetector.inspect_tool(self.tool_name)
        return info.version

    @abc.abstractmethod
    def execute(
        self,
        config: AutoSilixConfig,
        artifacts: ArtifactManager,
        mock: bool = False,
    ) -> StageResult:
        """Execute the stage using the tool or a validated mock."""
        pass

    def create_pending_result(self, log_path: Path) -> StageResult:
        return StageResult(
            name=self.stage_name,
            state=StageState.RUNNING,
            start_time=datetime.now(timezone.utc).isoformat(),
            log_file=str(log_path),
        )

    def mark_passed(
        self,
        result: StageResult,
        duration: float,
        artifacts: list[str],
        exit_code: int = 0,
    ) -> StageResult:
        result.state = StageState.PASS
        result.end_time = datetime.now(timezone.utc).isoformat()
        result.duration_seconds = duration
        result.exit_code = exit_code
        result.artifacts = artifacts
        return result

    def mark_failed(
        self,
        result: StageResult,
        duration: float,
        error_summary: str,
        exit_code: int = 1,
    ) -> StageResult:
        result.state = StageState.FAIL
        result.end_time = datetime.now(timezone.utc).isoformat()
        result.duration_seconds = duration
        result.exit_code = exit_code
        result.error_summary = error_summary
        return result

    def mark_unsupported(
        self,
        result: StageResult,
        reason: str,
    ) -> StageResult:
        result.state = StageState.UNSUPPORTED
        result.end_time = datetime.now(timezone.utc).isoformat()
        result.error_summary = reason
        result.exit_code = None
        return result
