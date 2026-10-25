"""Configuration loading, validation, path resolution, and schema enforcement."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from autosilix.exceptions import ConfigurationError, ValidationError


@dataclass
class DesignConfig:
    name: str
    top_module: str
    rtl_files: list[str]
    tb_files: list[str] = field(default_factory=list)
    constraints_file: str | None = None


@dataclass
class PDKConfig:
    name: str
    variant: str = "sky130_fd_sc_hd"
    std_cell_library: str = "sky130_fd_sc_hd"
    pdk_root: str = "/usr/local/share/pdk"


@dataclass
class ConstraintsConfig:
    clock_period: float = 10.0
    clock_port: str = "clk"
    clock_uncertainty: float = 0.25
    input_delay: float = 2.0
    output_delay: float = 2.0
    time_unit: str = "ns"
    cap_unit: str = "pF"


@dataclass
class PhysicalConfig:
    core_utilization: float = 0.35
    core_aspect_ratio: float = 1.0
    core_margin: float = 10.0
    die_area: list[float] | None = None
    core_area: list[float] | None = None


@dataclass
class SynthesisConfig:
    strategy: str = "AREA"
    flatten: bool = True
    abc_clock_period: float = 10000.0


@dataclass
class FlowConfig:
    stages: list[str] = field(
        default_factory=lambda: [
            "rtl_simulation",
            "synthesis",
            "floorplan",
            "power_planning",
            "placement",
            "cts",
            "routing",
            "sta",
            "gds_export",
        ]
    )
    timeouts: dict[str, int] = field(
        default_factory=lambda: {
            "rtl_simulation": 120,
            "synthesis": 300,
            "floorplan": 180,
            "power_planning": 180,
            "placement": 300,
            "cts": 300,
            "routing": 600,
            "sta": 180,
            "drc": 300,
            "lvs": 300,
            "gds_export": 180,
        }
    )
    fail_fast: bool = True


@dataclass
class AutoSilixConfig:
    schema_version: str
    design: DesignConfig
    pdk: PDKConfig
    flow: FlowConfig
    constraints: ConstraintsConfig = field(default_factory=ConstraintsConfig)
    physical: PhysicalConfig = field(default_factory=PhysicalConfig)
    synthesis: SynthesisConfig = field(default_factory=SynthesisConfig)
    config_path: str | None = None
    raw_dict: dict[str, Any] = field(default_factory=dict)
    config_hash: str = ""

    def get_stage_timeout(self, stage_name: str) -> int:
        return self.flow.timeouts.get(stage_name, 300)


class ConfigManager:
    """Loads and validates AutoSilix configuration files."""

    @staticmethod
    def get_schema_path() -> Path:
        """Locate schemas/config.schema.json relative to repository root."""
        # Try local schemas directory
        cur = Path(__file__).resolve().parent
        for _ in range(4):
            candidate = cur / "schemas" / "config.schema.json"
            if candidate.exists():
                return candidate
            cur = cur.parent
        # Default fallback to cwd
        return Path("schemas/config.schema.json").resolve()

    @classmethod
    def load_schema(cls) -> dict[str, Any]:
        schema_path = cls.get_schema_path()
        if not schema_path.exists():
            raise ConfigurationError(
                f"Configuration JSON schema not found at {schema_path}",
                details="Verify repository structure contains schemas/config.schema.json",
            )
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise ConfigurationError(f"Failed to parse config schema: {e}") from e

    @classmethod
    def load(cls, config_path: str | Path, workspace_root: str | Path | None = None) -> AutoSilixConfig:
        path = Path(config_path).resolve()
        if not path.is_file():
            raise ConfigurationError(f"Configuration file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                raw_dict = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Malformed YAML in {path}: {e}") from e
        except Exception as e:
            raise ConfigurationError(f"Failed to read config file {path}: {e}") from e

        if not isinstance(raw_dict, dict):
            raise ConfigurationError(f"Configuration at {path} must be a YAML dictionary")

        # Validate against JSON Schema
        schema = cls.load_schema()
        validator = jsonschema.Draft202012Validator(schema)
        errors = list(validator.iter_errors(raw_dict))
        if errors:
            err_msgs = [f"  - {err.json_path}: {err.message}" for err in errors]
            raise ValidationError(
                f"Configuration validation failed for {path.name}:\n" + "\n".join(err_msgs),
                details=str(errors[0].message),
            )

        # Compute deterministic SHA256 of configuration content
        config_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Determine reference directory for relative path resolution
        # Preference: if workspace_root given, use that; else directory containing config file
        base_dir = Path(workspace_root).resolve() if workspace_root else path.parent
        # If config is inside configs/designs, base_dir might be project root
        if not workspace_root and "configs" in path.parts:
            # Step up to project root
            idx = path.parts.index("configs")
            base_dir = Path(*path.parts[:idx])

        # Resolve design file paths
        d_raw = raw_dict["design"]
        resolved_rtl = [cls._resolve_path(f, base_dir) for f in d_raw["rtl_files"]]
        resolved_tb = [cls._resolve_path(f, base_dir) for f in d_raw.get("tb_files", [])]
        resolved_sdc = cls._resolve_path(d_raw.get("constraints_file"), base_dir) if d_raw.get("constraints_file") else None

        # Verify RTL files exist
        for rtl in resolved_rtl:
            if not Path(rtl).is_file():
                raise ConfigurationError(
                    f"RTL source file declared in configuration not found: {rtl}",
                    details=f"Resolved against base path: {base_dir}",
                )

        design_cfg = DesignConfig(
            name=d_raw["name"],
            top_module=d_raw["top_module"],
            rtl_files=resolved_rtl,
            tb_files=resolved_tb,
            constraints_file=resolved_sdc,
        )

        p_raw = raw_dict.get("pdk", {})
        pdk_cfg = PDKConfig(
            name=p_raw.get("name", "sky130"),
            variant=p_raw.get("variant", "sky130_fd_sc_hd"),
            std_cell_library=p_raw.get("std_cell_library", "sky130_fd_sc_hd"),
            pdk_root=p_raw.get("pdk_root", "/usr/local/share/pdk"),
        )

        c_raw = raw_dict.get("constraints", {})
        const_cfg = ConstraintsConfig(
            clock_period=float(c_raw.get("clock_period", 10.0)),
            clock_port=str(c_raw.get("clock_port", "clk")),
            clock_uncertainty=float(c_raw.get("clock_uncertainty", 0.25)),
            input_delay=float(c_raw.get("input_delay", 2.0)),
            output_delay=float(c_raw.get("output_delay", 2.0)),
            time_unit=str(c_raw.get("time_unit", "ns")),
            cap_unit=str(c_raw.get("cap_unit", "pF")),
        )

        phys_raw = raw_dict.get("physical", {})
        phys_cfg = PhysicalConfig(
            core_utilization=float(phys_raw.get("core_utilization", 0.35)),
            core_aspect_ratio=float(phys_raw.get("core_aspect_ratio", 1.0)),
            core_margin=float(phys_raw.get("core_margin", 10.0)),
            die_area=phys_raw.get("die_area"),
            core_area=phys_raw.get("core_area"),
        )

        s_raw = raw_dict.get("synthesis", {})
        synth_cfg = SynthesisConfig(
            strategy=s_raw.get("strategy", "AREA"),
            flatten=bool(s_raw.get("flatten", True)),
            abc_clock_period=float(s_raw.get("abc_clock_period", 10000.0)),
        )

        f_raw = raw_dict.get("flow", {})
        flow_cfg = FlowConfig(
            stages=f_raw.get("stages", FlowConfig().stages),
            timeouts=f_raw.get("timeouts", FlowConfig().timeouts),
            fail_fast=bool(f_raw.get("fail_fast", True)),
        )

        return AutoSilixConfig(
            schema_version=raw_dict.get("schema_version", "1.0.0"),
            design=design_cfg,
            pdk=pdk_cfg,
            constraints=const_cfg,
            physical=phys_cfg,
            synthesis=synth_cfg,
            flow=flow_cfg,
            config_path=str(path),
            raw_dict=raw_dict,
            config_hash=config_hash,
        )

    @staticmethod
    def _resolve_path(file_path: str | None, base_dir: Path) -> str | None:
        if file_path is None:
            return None
        p = Path(file_path)
        if p.is_absolute():
            return str(p)
        # Try relative to base_dir
        rel = (base_dir / p).resolve()
        if rel.exists():
            return str(rel)
        # Try relative to cwd
        cwd_p = Path(file_path).resolve()
        if cwd_p.exists():
            return str(cwd_p)
        return str(rel)
