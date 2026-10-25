"""Artifact management, run isolation, directory structure, and integrity hashing."""

from __future__ import annotations

import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from autosilix.exceptions import ArtifactError


class ArtifactManager:
    """Manages isolated run directories and generated EDA artifacts."""

    SUBDIRECTORIES = [
        "config",
        "logs",
        "reports",
        "netlists",
        "databases",
        "layout",
        "metrics",
    ]

    def __init__(
        self,
        design_name: str,
        run_id: str | None = None,
        base_runs_dir: str | Path = "runs",
    ) -> None:
        self.design_name = design_name
        self.base_runs_dir = Path(base_runs_dir).resolve()

        if run_id:
            self.run_id = run_id
        else:
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            # 6-char hex suffix for collision prevention
            rand_hex = hashlib.sha256(f"{ts}_{os.getpid()}".encode()).hexdigest()[:6]
            self.run_id = f"run_{ts}_{rand_hex}"

        self.run_dir = self.base_runs_dir / self.design_name / self.run_id

    def initialize_run_dir(self, overwrite: bool = False) -> Path:
        """Create isolated run directory structure."""
        if self.run_dir.exists():
            if not overwrite and any(self.run_dir.iterdir()):
                raise ArtifactError(
                    f"Run directory already exists and is not empty: {self.run_dir}",
                    details="Specify a new run ID or allow unique automatic ID generation",
                )

        self.run_dir.mkdir(parents=True, exist_ok=True)
        for sub in self.SUBDIRECTORIES:
            (self.run_dir / sub).mkdir(parents=True, exist_ok=True)

        return self.run_dir

    def get_path(self, relative_path: str) -> Path:
        """Get absolute path to a file inside the run directory."""
        return self.run_dir / relative_path

    def get_log_path(self, stage_name: str) -> Path:
        """Get path to a stage's log file."""
        return self.run_dir / "logs" / f"{stage_name}.log"

    def snapshot_config(self, raw_config: dict[str, Any]) -> Path:
        """Save effective configuration snapshot inside run directory."""
        dest = self.run_dir / "config" / "effective_config.yaml"
        with open(dest, "w", encoding="utf-8") as f:
            yaml.safe_dump(raw_config, f, sort_keys=False)
        return dest

    @staticmethod
    def compute_sha256(file_path: str | Path) -> str:
        """Compute SHA256 checksum of a file."""
        p = Path(file_path)
        if not p.is_file():
            return ""
        hasher = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def record_artifact(self, relative_dest: str, src_path: str | Path) -> str:
        """Copy or save an artifact into the run directory and return relative path."""
        dest = self.run_dir / relative_dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest)
        return relative_dest

    def list_artifacts(self) -> list[str]:
        """List all generated files inside the run directory relative to run_dir."""
        if not self.run_dir.exists():
            return []
        artifacts = []
        for p in self.run_dir.rglob("*"):
            if p.is_file() and p.name != "manifest.json":
                rel = p.relative_to(self.run_dir).as_posix()
                artifacts.append(rel)
        return sorted(artifacts)
