"""Stage-oriented workflow engine with dependency enforcement and manifest tracking."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from autosilix.adapters import get_adapter_for_stage
from autosilix.artifacts import ArtifactManager
from autosilix.manifest import Manifest
from autosilix.metrics import MetricsExtractor
from autosilix.stages import STAGE_DEPENDENCIES, STAGE_ORDER, StageResult, StageState

if TYPE_CHECKING:
    from autosilix.config import AutoSilixConfig

logger = logging.getLogger("autosilix.workflow")


class WorkflowEngine:
    """Orchestrates end-to-end execution of digital implementation flows."""

    def __init__(
        self,
        config: AutoSilixConfig,
        run_id: str | None = None,
        base_runs_dir: str | Path = "runs",
        mock: bool = False,
        selected_stages: list[str] | None = None,
    ) -> None:
        self.config = config
        self.mock = mock
        self.artifacts = ArtifactManager(
            design_name=config.design.name,
            run_id=run_id,
            base_runs_dir=base_runs_dir,
        )

        # Determine stages to execute
        all_stages = config.flow.stages
        if selected_stages:
            # Maintain standard topological order
            self.stages_to_run = [s for s in STAGE_ORDER if s in selected_stages and s in all_stages]
        else:
            self.stages_to_run = [s for s in STAGE_ORDER if s in all_stages]

        self.manifest: Manifest | None = None

    def run(self) -> Manifest:
        """Execute the configured workflow."""
        # 1. Initialize run directory and snapshot config
        run_dir = self.artifacts.initialize_run_dir()
        self.artifacts.snapshot_config(self.config.raw_dict)

        # 2. Initialize manifest
        self.manifest = Manifest(
            run_id=self.artifacts.run_id,
            design_name=self.config.design.name,
            config_hash=self.config.config_hash,
            run_dir=run_dir,
        )
        self.manifest.set_status("RUNNING")

        failed_stages: set[str] = set()
        completed_stages: set[str] = set()

        for stage_name in self.stages_to_run:
            # Check prerequisites
            prereqs = STAGE_DEPENDENCIES.get(stage_name, [])
            unsatisfied = [p for p in prereqs if p in self.stages_to_run and p not in completed_stages]

            if unsatisfied or (self.config.flow.fail_fast and failed_stages):
                # Skip this stage
                res = StageResult(
                    name=stage_name,
                    state=StageState.SKIPPED,
                    error_summary=f"Skipped due to unsatisfied prerequisite(s): {unsatisfied}" if unsatisfied else "Skipped due to prior stage failure",
                )
                self.manifest.update_stage(res)
                continue

            # Execute stage via adapter
            try:
                adapter = get_adapter_for_stage(stage_name)
                res = adapter.execute(self.config, self.artifacts, mock=self.mock)
            except Exception as e:
                res = StageResult(
                    name=stage_name,
                    state=StageState.FAIL,
                    error_summary=f"Stage execution exception: {e}",
                    exit_code=1,
                )

            self.manifest.update_stage(res)

            if res.state == StageState.PASS:
                completed_stages.add(stage_name)
            elif res.state in (StageState.SKIPPED, StageState.UNSUPPORTED):
                # Unsupported stages do not block downstream unless strictly critical
                completed_stages.add(stage_name)
            else:
                failed_stages.add(stage_name)
                self.manifest.record_error(f"Stage '{stage_name}' failed: {res.error_summary}")
                if self.config.flow.fail_fast:
                    logger.warning(f"Fail-fast enabled; aborting after failure in stage '{stage_name}'")

        # 3. Extract metrics
        try:
            metrics = MetricsExtractor.extract_all(self.artifacts.run_dir)
            self.manifest.set_metrics(metrics)
        except Exception as e:
            self.manifest.record_warning(f"Metrics extraction warning: {e}")

        # 4. Finalize manifest
        self.manifest.finalize()
        return self.manifest
