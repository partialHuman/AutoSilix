"""Subprocess execution manager with timeouts, logging, and process tree cleanup."""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from autosilix.exceptions import ToolNotFoundError


@dataclass
class CommandExecutionResult:
    command: list[str]
    returncode: int
    duration_seconds: float
    timed_out: bool = False
    stdout: str = ""
    stderr: str = ""


class SubprocessRunner:
    """Safely executes tool commands, manages timeouts, and captures logs."""

    @staticmethod
    def run_command(
        cmd: list[str],
        log_file: Path | str | None = None,
        cwd: Path | str | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
        capture_memory: bool = False,
    ) -> CommandExecutionResult:
        """Run a process, stream its output to a log file, and enforce timeout."""
        if not cmd:
            raise ValueError("Command list cannot be empty")

        # Check executable existence
        exec_path = cmd[0]
        # Environment variables merge
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        start_time = time.monotonic()
        timed_out = False
        log_f = None

        try:
            if log_file:
                log_p = Path(log_file)
                log_p.parent.mkdir(parents=True, exist_ok=True)
                log_f = open(log_p, "a", encoding="utf-8")
                log_f.write(f"\n[AUTOSILIX] Executing: {' '.join(cmd)}\n")
                log_f.flush()

            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd) if cwd else None,
                env=merged_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            try:
                stdout_data, stderr_data = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                proc.kill()
                stdout_data, stderr_data = proc.communicate()

            duration = time.monotonic() - start_time

            if log_f:
                if stdout_data:
                    log_f.write(stdout_data)
                if stderr_data:
                    log_f.write("\n[STDERR]\n")
                    log_f.write(stderr_data)
                if timed_out:
                    log_f.write(f"\n[AUTOSILIX ERROR] Command timed out after {timeout} seconds\n")
                log_f.write(f"\n[AUTOSILIX] Process exited with code {proc.returncode} in {duration:.2f}s\n")
                log_f.flush()

            return CommandExecutionResult(
                command=cmd,
                returncode=proc.returncode,
                duration_seconds=duration,
                timed_out=timed_out,
                stdout=stdout_data if capture_memory else "",
                stderr=stderr_data if capture_memory else "",
            )

        except FileNotFoundError as e:
            if log_f:
                log_f.write(f"\n[AUTOSILIX ERROR] Executable not found: {exec_path}\n")
                log_f.flush()
            raise ToolNotFoundError(
                f"Executable not found: '{exec_path}'",
                details="Ensure tool is installed and accessible on PATH or configured in PDK/flow",
            ) from e
        finally:
            if log_f:
                log_f.close()
