"""AutoSilix Tool Adapters."""

from autosilix.adapters.base import ToolAdapter
from autosilix.adapters.klayout import KLayoutAdapter
from autosilix.adapters.magic import MagicAdapter
from autosilix.adapters.openroad import OpenRoadAdapter
from autosilix.adapters.simulator import SimulatorAdapter
from autosilix.adapters.yosys import YosysAdapter


def get_adapter_for_stage(stage_name: str) -> ToolAdapter:
    """Return the registered ToolAdapter instance for a given stage."""
    if stage_name == "rtl_simulation":
        return SimulatorAdapter()
    elif stage_name == "synthesis":
        return YosysAdapter()
    elif stage_name in ("floorplan", "power_planning", "placement", "cts", "routing", "sta", "gds_export"):
        return OpenRoadAdapter(stage_name=stage_name)
    elif stage_name == "drc":
        return KLayoutAdapter()
    elif stage_name == "lvs":
        return MagicAdapter(stage_name="lvs")
    else:
        raise ValueError(f"Unknown workflow stage: '{stage_name}'")


__all__ = [
    "ToolAdapter",
    "SimulatorAdapter",
    "YosysAdapter",
    "OpenRoadAdapter",
    "KLayoutAdapter",
    "MagicAdapter",
    "get_adapter_for_stage",
]
