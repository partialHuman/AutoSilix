"""Manifest generation, persistence, provenance tracking, and schema validation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autosilix.exceptions import ManifestError
from autosilix.stages import StageResult, StageState
from autosilix.toolchain import ToolchainDetector


class Manifest:
    """Represents an AutoSilix run manifest recording full provenance and stage results."""

    SCHEMA_VERSION = "1.0.0"

    def __init__(
        self,
        run_id: str,
        design_name: str,
        config_hash: str,
        run_dir: Path,
        workspace_dir: str | Path | None = None,
    ) -> None:
        self.run_id = run_id
        self.design_name = design_name
        self.config_hash = config_hash
        self.run_dir = Path(run_dir).resolve()
        self.manifest_path = self.run_dir / "manifest.json"

        self.status = "PENDING"
        self.start_time: str = datetime.now(timezone.utc).isoformat()
        self.end_time: str | None = None
        self.duration_seconds: float | None = None

        env = ToolchainDetector.get_environment_info(str(workspace_dir) if workspace_dir else None)
        self.git_commit = env.get("git_commit")
        self.git_dirty = env.get("git_dirty")
        self.environment = env

        self.stages: dict[str, StageResult] = {}
        self.metrics: dict[str, dict[str, Any]] = {}
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.save()

    def set_status(self, status: str) -> None:
        self.status = status

    def update_stage(self, stage_result: StageResult) -> None:
        self.stages[stage_result.name] = stage_result
        self.save()

    def record_error(self, err_msg: str) -> None:
        self.errors.append(err_msg)
        self.save()

    def record_warning(self, warn_msg: str) -> None:
        self.warnings.append(warn_msg)
        self.save()

    def set_metrics(self, metrics: dict[str, dict[str, Any]]) -> None:
        self.metrics = metrics
        self.save()

    def finalize(self, final_status: str | None = None) -> None:
        """Mark workflow completion, calculate duration, and persist."""
        now = datetime.now(timezone.utc)
        self.end_time = now.isoformat()
        start_dt = datetime.fromisoformat(self.start_time)
        self.duration_seconds = round((now - start_dt).total_seconds(), 3)

        if final_status:
            self.status = final_status
        else:
            # Determine from stage states
            all_passed = all(
                s.state in (StageState.PASS, StageState.SKIPPED, StageState.UNSUPPORTED)
                for s in self.stages.values()
            )
            has_fail = any(s.state == StageState.FAIL for s in self.stages.values())
            if has_fail:
                self.status = "FAIL"
            elif all_passed and self.stages:
                self.status = "PASS"
            else:
                self.status = "FAIL"

        self.save()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "run_id": self.run_id,
            "design_name": self.design_name,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "config_hash": self.config_hash,
            "git_commit": self.git_commit,
            "git_dirty": self.git_dirty,
            "environment": self.environment,
            "stages": {k: v.to_dict() for k, v in self.stages.items()},
            "metrics": self.metrics,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def save(self) -> None:
        """Atomically persist manifest to run_dir/manifest.json."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        temp_path = self.run_dir / "manifest.json.tmp"
        data = self.to_dict()

        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        temp_path.replace(self.manifest_path)

    @classmethod
    def load(cls, manifest_path: str | Path) -> dict[str, Any]:
        """Load and return manifest data dictionary."""
        p = Path(manifest_path).resolve()
        if not p.is_file():
            raise ManifestError(f"Manifest file not found: {p}")
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise ManifestError(f"Failed to read manifest at {p}: {e}") from e
