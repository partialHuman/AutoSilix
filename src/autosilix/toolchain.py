"""Toolchain discovery, availability detection, and environment inventory."""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass


@dataclass
class ToolInfo:
    """Information regarding an EDA tool or utility."""

    name: str
    command: str
    available: bool
    path: str | None = None
    version: str | None = None
    category: str = "eda"

    def to_dict(self) -> dict:
        return asdict(self)


KNOWN_TOOLS: dict[str, dict[str, str]] = {
    "iverilog": {
        "command": "iverilog",
        "category": "simulation",
        "version_flag": "-V",
        "version_pattern": r"Icarus Verilog version (\S+)",
    },
    "vvp": {
        "command": "vvp",
        "category": "simulation",
        "version_flag": "-V",
        "version_pattern": r"Icarus Verilog runtime version (\S+)",
    },
    "verilator": {
        "command": "verilator",
        "category": "simulation",
        "version_flag": "--version",
        "version_pattern": r"Verilator (\S+)",
    },
    "yosys": {
        "command": "yosys",
        "category": "synthesis",
        "version_flag": "-V",
        "version_pattern": r"Yosys (\S+)",
    },
    "openroad": {
        "command": "openroad",
        "category": "physical_design",
        "version_flag": "-version",
        "version_pattern": r"OpenROAD (\S+)",
    },
    "klayout": {
        "command": "klayout",
        "category": "layout_inspection",
        "version_flag": "-v",
        "version_pattern": r"KLayout (\S+)",
    },
    "magic": {
        "command": "magic",
        "category": "physical_verification",
        "version_flag": "--version",
        "version_pattern": r"(\S+)",
    },
    "git": {
        "command": "git",
        "category": "vcs",
        "version_flag": "--version",
        "version_pattern": r"git version (\S+)",
    },
}


class ToolchainDetector:
    """Detects and reports installed EDA tools and system environment."""

    @staticmethod
    def inspect_tool(name: str) -> ToolInfo:
        spec = KNOWN_TOOLS.get(name, {"command": name, "category": "custom", "version_flag": "--version"})
        cmd = spec["command"]
        category = spec.get("category", "custom")
        found_path = shutil.which(cmd)

        if not found_path:
            return ToolInfo(name=name, command=cmd, available=False, category=category)

        version = None
        v_flag = spec.get("version_flag", "--version")
        v_pattern = spec.get("version_pattern")

        try:
            res = subprocess.run(
                [found_path, v_flag],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            output = (res.stdout or "") + (res.stderr or "")
            if v_pattern:
                m = re.search(v_pattern, output)
                if m:
                    version = m.group(1).strip()
            if not version and output:
                # Fallback to first line
                first_line = output.strip().splitlines()[0]
                version = first_line[:60].strip()
        except Exception:
            version = "unknown"

        return ToolInfo(
            name=name,
            command=cmd,
            available=True,
            path=found_path,
            version=version,
            category=category,
        )

    @classmethod
    def get_inventory(cls) -> dict[str, ToolInfo]:
        """Inspect all known tools and return inventory dictionary."""
        return {name: cls.inspect_tool(name) for name in KNOWN_TOOLS}

    @staticmethod
    def get_git_info(workspace_dir: str | None = None) -> tuple[str | None, bool | None]:
        """Return (commit_hash, is_dirty) for the current git repository."""
        cwd = workspace_dir or os.getcwd()
        if not shutil.which("git"):
            return None, None

        try:
            c_res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if c_res.returncode != 0:
                return None, None
            commit_hash = c_res.stdout.strip()

            s_res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            is_dirty = bool(s_res.stdout.strip())
            return commit_hash, is_dirty
        except Exception:
            return None, None

    @classmethod
    def get_environment_info(cls, workspace_dir: str | None = None) -> dict:
        """Capture full reproducible system and tool inventory."""
        commit_hash, is_dirty = cls.get_git_info(workspace_dir)
        tools = {k: v.to_dict() for k, v in cls.get_inventory().items()}

        return {
            "os": platform.platform(),
            "python_version": sys.version.split()[0],
            "hostname": platform.node(),
            "architecture": platform.machine(),
            "git_commit": commit_hash,
            "git_dirty": is_dirty,
            "tools": tools,
        }
